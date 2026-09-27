import base64
import hashlib
import io
import time
import warnings
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select

from app.core.errors import AppError
from app.models.entities import MediaCleanup, Product, ProductImage

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_IMAGES = 12
PREFIX = "your-sanctuary/products/"
FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def normalized_image(data, content_type):
    if not data or len(data) > MAX_BYTES:
        raise AppError(413, "image_size", "Choose an image up to 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                fmt = im.format
                if fmt not in FORMATS or content_type != FORMATS[fmt]:
                    raise ValueError("format")
                if getattr(im, "n_frames", 1) != 1:
                    raise ValueError("animation")
                if im.width * im.height > MAX_PIXELS or max(im.size) > 8000:
                    raise ValueError("dimensions")
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                im = ImageOps.exif_transpose(im)
                im = im.convert(
                    "RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB"
                )
                # Re-encode pixels only: discard EXIF/GPS, comments and appended payloads.
                clean = Image.new(im.mode, im.size)
                clean.paste(im)
                out = io.BytesIO()
                clean.save(out, format=fmt, quality=90)
                result = out.getvalue()
                if len(result) > MAX_BYTES:
                    raise AppError(
                        413, "image_size", "Decoded image is too large. Export a smaller image."
                    )
                return result, fmt.lower().replace("jpeg", "jpg"), clean.width, clean.height
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise AppError(
            422,
            "invalid_image",
            "Use a valid, static JPEG, PNG or WebP image, at most 20 megapixels and 8000 pixels per side.",
        ) from None


class Cloudinary:
    def __init__(self, settings):
        self.cloud = settings.cloudinary_cloud_name
        self.key = settings.cloudinary_api_key.get_secret_value()
        self.secret = settings.cloudinary_api_secret.get_secret_value()
        self.enabled = bool(self.cloud and self.key and self.secret)

    def call(self, action, params, file=None):
        if not self.enabled:
            raise AppError(503, "media_unavailable", "Cloudinary uploads are not configured yet.")
        params = {**params, "timestamp": str(int(time.time()))}
        payload = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + self.secret
        form = {
            **params,
            "api_key": self.key,
            "signature": hashlib.sha256(payload.encode()).hexdigest(),
        }
        if file is not None:
            form["file"] = "data:application/octet-stream;base64," + base64.b64encode(file).decode()
        try:
            with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
                response = client.post(
                    f"https://api.cloudinary.com/v1_1/{self.cloud}/image/{action}", data=form
                )
                response.raise_for_status()
                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError("Expected object")
                return result
        except (httpx.HTTPError, ValueError):
            # Provider bodies can contain account details. Never forward or log them.
            raise AppError(
                502, "media_provider", "Cloudinary could not complete this request. Please retry."
            ) from None

    def upload(self, data, public_id, fmt, width, height):
        result = self.call(
            "upload",
            {"public_id": public_id, "overwrite": "false", "allowed_formats": "jpg,png,webp"},
            data,
        )
        url = urlsplit(result.get("secure_url", ""))
        if (
            result.get("public_id") != public_id
            or result.get("resource_type") != "image"
            or result.get("format") != fmt
            or result.get("width") != width
            or result.get("height") != height
            or url.scheme != "https"
            or url.netloc != "res.cloudinary.com"
            or not url.path.startswith(f"/{self.cloud}/image/upload/")
            or url.query
            or url.fragment
        ):
            raise AppError(
                502, "media_response", "Cloudinary returned an unexpected image response."
            )
        return result["secure_url"]

    def destroy(self, public_id):
        if not public_id.startswith(PREFIX):
            raise AppError(
                409, "media_scope", "Asset is outside this store's managed upload folder."
            )
        result = self.call("destroy", {"public_id": public_id, "invalidate": "true"})
        if result.get("result") not in {"ok", "not found"}:
            raise AppError(502, "media_delete", "Cloudinary deletion is pending retry.")


def lock_product(db, product_id):
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if product is None:
        raise AppError(404, "not_found", "Product not found.")
    return product


def images(db, product_id):
    return list(
        db.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.position)
            .execution_options(populate_existing=True)
        )
    )


def view(row):
    return dict(
        id=str(row.id),
        public_id=row.public_id,
        url=row.url,
        alt=row.alt,
        width=row.width,
        height=row.height,
        position=row.position,
        format=row.format,
        byte_size=row.byte_size,
        managed=bool(row.cloud_name),
    )


def arrange(db, rows):
    # Two phases avoid the immediate unique(product_id, position) constraint during swaps.
    offset = max((r.position for r in rows), default=0) + len(rows) + 1
    for n, row in enumerate(rows):
        row.position = offset + n
    db.flush()
    for n, row in enumerate(rows):
        row.position = n
    db.flush()


def enqueue(db, row):
    if row.cloud_name:
        db.add(
            MediaCleanup(
                cloud_name=row.cloud_name,
                public_id=row.public_id,
                not_before=datetime.now(timezone.utc),
            )
        )


def upload(db, product_id, data, content_type, alt, gateway, replace_id=None):
    if not gateway.enabled:
        raise AppError(503, "media_unavailable", "Cloudinary uploads are not configured yet.")
    data, fmt, width, height = normalized_image(data, content_type)
    lock_product(db, product_id)
    rows = images(db, product_id)
    old = next((r for r in rows if r.id == replace_id), None)
    if replace_id and old is None:
        raise AppError(404, "not_found", "Image not found for this product.")
    if not replace_id and len(rows) >= MAX_IMAGES:
        raise AppError(409, "image_limit", "A product supports up to 12 images.")
    public_id = PREFIX + str(product_id) + "/" + uuid4().hex
    intent = MediaCleanup(
        cloud_name=gateway.cloud,
        public_id=public_id,
        not_before=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(intent)
    db.commit()  # Durable orphan cleanup before the external side effect.
    try:
        if (
            db.scalar(select(MediaCleanup).where(MediaCleanup.id == intent.id).with_for_update())
            is None
        ):
            raise AppError(409, "upload_expired", "Upload expired. Please retry.")
        lock_product(db, product_id)
        rows = images(db, product_id)
        old = next((r for r in rows if r.id == replace_id), None)
        if replace_id and old is None:
            raise AppError(409, "image_changed", "This image was removed. Refresh the editor.")
        if not replace_id and len(rows) >= MAX_IMAGES:
            raise AppError(409, "image_limit", "A product supports up to 12 images.")
        url = gateway.upload(data, public_id, fmt, width, height)
        if old:
            enqueue(db, old)
            row = old
        else:
            row = ProductImage(
                product_id=product_id, position=max((r.position for r in rows), default=-1) + 1
            )
            db.add(row)
            rows.append(row)
        row.public_id, row.url, row.alt = public_id, url, alt
        row.width, row.height, row.format, row.byte_size = width, height, fmt, len(data)
        row.cloud_name = gateway.cloud
        db.delete(intent)
        arrange(db, rows)
        db.commit()
        return [view(r) for r in rows]
    except Exception:
        db.rollback()  # The persisted intent survives, even after an uncertain upload outcome.
        raise


def cleanup(db, gateway, limit=20):
    if not gateway.enabled:
        raise AppError(503, "media_unavailable", "Configure Cloudinary before cleanup.")
    done = failed = 0
    for _ in range(limit):
        job = db.scalar(
            select(MediaCleanup)
            .where(
                MediaCleanup.cloud_name == gateway.cloud,
                MediaCleanup.not_before <= datetime.now(timezone.utc),
            )
            .order_by(MediaCleanup.not_before)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            break
        if db.scalar(
            select(ProductImage.id).where(
                ProductImage.public_id == job.public_id, ProductImage.cloud_name == job.cloud_name
            )
        ):
            db.delete(job)
        else:
            try:
                gateway.destroy(job.public_id)
                db.delete(job)
                done += 1
            except AppError:
                job.attempts += 1
                job.not_before = datetime.now(timezone.utc) + timedelta(
                    minutes=min(60, 2 ** min(job.attempts, 6))
                )
                failed += 1
        db.commit()
    return dict(deleted=done, pending_retry=failed)
