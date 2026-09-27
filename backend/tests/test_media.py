import hashlib
import io
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs
from uuid import uuid4

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import func, select
from test_auth import csrf, login, register
from test_catalog import admin_headers as admin_fixture
from test_catalog import item as item_fixture

from app.api.media import provider
from app.config import Settings
from app.core.errors import AppError
from app.models.entities import MediaCleanup, ProductImage
from app.services import media

admin_headers = admin_fixture
item = item_fixture


def photo(fmt="PNG", size=(40, 50)):
    out = io.BytesIO()
    Image.new("RGB", size, "beige").save(out, format=fmt)
    return out.getvalue()


class FakeCloud:
    enabled = True
    cloud = "test-store"
    fail_upload = False
    fail_delete = False

    def __init__(self):
        self.uploads = []
        self.deletes = []

    def upload(self, data, public_id, fmt, width, height):
        self.uploads.append(public_id)
        if self.fail_upload:
            raise AppError(502, "media_provider", "Upload unavailable")
        return f"https://res.cloudinary.com/{self.cloud}/image/upload/v1/{public_id}.{fmt}"

    def destroy(self, public_id):
        self.deletes.append(public_id)
        if self.fail_delete:
            raise AppError(502, "media_provider", "Delete unavailable")


@pytest.fixture
def cloud(client):
    gateway = FakeCloud()
    client.app.dependency_overrides[provider] = lambda: gateway
    return gateway


def upload(client, item, headers, data=None, kind="image/png", **params):
    return client.post(
        f"/api/v1/admin/products/{item[0].id}/media/upload",
        params={"alt": "Ceramic vase front view", **params},
        content=photo() if data is None else data,
        headers={**headers, "Content-Type": kind},
    )


@pytest.mark.parametrize(
    "fmt,kind", [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")]
)
def test_decode_supported_formats_and_strip_metadata(fmt, kind):
    original = photo(fmt) + b"PRIVATE_METADATA"
    data, _, width, height = media.normalized_image(original, kind)
    assert (width, height) == (40, 50)
    assert b"PRIVATE_METADATA" not in data
    with Image.open(io.BytesIO(data)) as im:
        assert not im.getexif()


@pytest.mark.parametrize(
    "data,kind",
    [
        (b"<svg/>", "image/svg+xml"),
        (b"<script>alert(1)</script>", "image/png"),
        (photo(), "image/jpeg"),
        (photo("GIF"), "image/gif"),
        (photo()[:40], "image/png"),
        (photo(size=(8001, 1)), "image/png"),
    ],
)
def test_reject_invalid_images(data, kind):
    with pytest.raises(AppError):
        media.normalized_image(data, kind)


def test_animation_and_pixel_limit(monkeypatch):
    out = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(
        out, format="PNG", save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")]
    )
    with pytest.raises(AppError):
        media.normalized_image(out.getvalue(), "image/png")
    monkeypatch.setattr(media, "MAX_PIXELS", 100)
    with pytest.raises(AppError):
        media.normalized_image(photo(), "image/png")


def test_upload_replace_order_caption_delete(client, db, item, admin_headers, cloud):
    a = upload(client, item, admin_headers)
    assert a.status_code == 201, a.text
    first = a.json()[0]
    assert first["managed"] and first["format"] == "png" and first["byte_size"] > 0
    assert db.scalar(select(func.count()).select_from(MediaCleanup)) == 0
    rows = upload(client, item, admin_headers).json()
    path = f"/api/v1/admin/products/{item[0].id}/media"
    ids = [r["id"] for r in rows][::-1]
    ordered = client.patch(path + "/order", json={"image_ids": ids}, headers=admin_headers)
    assert ordered.status_code == 200, ordered.text
    assert [r["id"] for r in ordered.json()] == ids
    assert [r["position"] for r in ordered.json()] == [0, 1]
    assert (
        client.patch(
            path + "/order", json={"image_ids": [ids[0], ids[0]]}, headers=admin_headers
        ).status_code
        == 409
    )
    assert (
        client.patch(
            path + "/order", json={"image_ids": [str(uuid4()), ids[1]]}, headers=admin_headers
        ).status_code
        == 409
    )
    assert (
        client.patch(
            path + "/" + ids[0], json={"alt": "Vase alternate view"}, headers=admin_headers
        ).status_code
        == 200
    )
    replaced = upload(client, item, admin_headers, replace_id=first["id"])
    assert replaced.status_code == 201, replaced.text
    assert (
        next(r for r in replaced.json() if r["id"] == first["id"])["public_id"]
        != first["public_id"]
    )
    assert db.scalar(select(func.count()).select_from(MediaCleanup)) == 1
    assert media.cleanup(db, cloud)["deleted"] == 1
    assert cloud.deletes == [first["public_id"]]
    removed = client.delete(path + "/" + ids[0], headers=admin_headers)
    assert removed.status_code == 200 and removed.json()[0]["position"] == 0
    assert media.cleanup(db, cloud)["deleted"] == 1
    public = client.get(f"/api/v1/products/{item[0].id}").json()["images"]
    assert len(public) == 1 and public[0]["position"] == 0


def test_failure_preserves_old_image_and_cleanup_retries(client, db, item, admin_headers, cloud):
    original = upload(client, item, admin_headers).json()[0]
    cloud.fail_upload = True
    assert upload(client, item, admin_headers, replace_id=original["id"]).status_code == 502
    assert db.get(ProductImage, original["id"]).public_id == original["public_id"]
    job = db.scalar(select(MediaCleanup))
    assert job and job.public_id != original["public_id"]
    job.not_before = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    cloud.fail_delete = True
    assert media.cleanup(db, cloud) == {"deleted": 0, "pending_retry": 1}
    assert job.attempts == 1
    cloud.fail_delete = False
    job.not_before = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert media.cleanup(db, cloud)["deleted"] == 1


def test_upload_limits_ownership_auth_csrf(client, db, item, cloud):
    assert upload(client, item, {}).status_code == 401
    register(client)
    login(client)
    assert upload(client, item, csrf(client)).status_code == 403
    from app.models.entities import User

    db.scalar(select(User)).role = "admin"
    db.commit()
    assert upload(client, item, {}).status_code == 403
    headers = csrf(client)
    assert upload(client, item, headers, data=b"x" * (media.MAX_BYTES + 1)).status_code == 413
    assert upload(client, item, headers, data=b"not a photo").status_code == 422
    assert upload(client, item, headers, replace_id=str(uuid4())).status_code == 404
    assert upload(client, item, headers, alt="  ").status_code == 422
    assert cloud.uploads == []


def test_disabled_config_is_safe_and_legacy_images_still_work(client, db, item, admin_headers):
    config = client.get("/api/v1/admin/media/config").json()
    assert set(config) == {"enabled", "formats", "max_bytes", "max_images"}
    assert config["enabled"] is False
    assert upload(client, item, admin_headers).status_code == 503
    legacy = ProductImage(
        product_id=item[0].id,
        public_id="demo/vase",
        url="https://local-preview.invalid/demo/vase.png",
        alt="Demo vase",
        width=40,
        height=50,
        position=0,
    )
    db.add(legacy)
    db.commit()
    path = f"/api/v1/admin/products/{item[0].id}/media"
    assert client.get(path).json()[0]["managed"] is False
    assert client.delete(path + "/" + str(legacy.id), headers=admin_headers).status_code == 200
    assert db.scalar(select(func.count()).select_from(MediaCleanup)) == 0


def test_signed_provider_request_and_sanitized_errors(monkeypatch):
    settings = Settings(
        cloudinary_cloud_name="test-store",
        cloudinary_api_key=SecretStr("test-key"),
        cloudinary_api_secret=SecretStr("test-secret"),
    )
    gateway = media.Cloudinary(settings)
    real_client = httpx.Client

    def handler(req):
        form = {k: v[0] for k, v in parse_qs(req.content.decode()).items()}
        signed = {k: v for k, v in form.items() if k not in {"file", "api_key", "signature"}}
        expected = hashlib.sha256(
            ("&".join(f"{k}={v}" for k, v in sorted(signed.items())) + "test-secret").encode()
        ).hexdigest()
        assert form["signature"] == expected
        assert "test-secret" not in req.content.decode()
        assert form["invalidate"] == "true"
        return httpx.Response(200, json={"result": "ok"})

    monkeypatch.setattr(
        media.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    gateway.destroy(media.PREFIX + "fixture")

    def fail(req):
        return httpx.Response(401, text="test-secret test-key private account")

    monkeypatch.setattr(
        media.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(fail), **kwargs),
    )
    with pytest.raises(AppError) as error:
        gateway.destroy(media.PREFIX + "fixture")
    assert "test-secret" not in error.value.message
    with pytest.raises(AppError):
        gateway.destroy("another-project/image")


def test_association_failure_leaves_cleanup_intent(
    client, db, item, admin_headers, cloud, monkeypatch
):
    def fail(*args):
        raise AppError(409, "fixture_failure", "Database association failed")

    monkeypatch.setattr(media, "arrange", fail)
    assert upload(client, item, admin_headers).status_code == 409
    assert len(cloud.uploads) == 1
    assert db.scalar(select(func.count()).select_from(ProductImage)) == 0
    assert db.scalar(select(MediaCleanup)).public_id == cloud.uploads[0]


def test_limit_and_cleanup_never_deletes_attached_asset(
    client, db, item, admin_headers, cloud, monkeypatch
):
    monkeypatch.setattr(media, "MAX_IMAGES", 1)
    image = upload(client, item, admin_headers).json()[0]
    assert upload(client, item, admin_headers).status_code == 409
    assert len(cloud.uploads) == 1
    db.add(
        MediaCleanup(
            cloud_name=cloud.cloud,
            public_id=image["public_id"],
            not_before=datetime.now(timezone.utc),
        )
    )
    db.commit()
    assert media.cleanup(db, cloud)["deleted"] == 0
    assert not cloud.deletes


def test_upload_provider_contract(monkeypatch):
    gateway = media.Cloudinary(Settings(cloudinary_cloud_name="store"))
    pid = media.PREFIX + "fixture"
    response = dict(
        public_id=pid,
        resource_type="image",
        format="png",
        width=40,
        height=50,
        secure_url=f"https://res.cloudinary.com/store/image/upload/v1/{pid}.png",
    )
    monkeypatch.setattr(gateway, "call", lambda *a, **k: response)
    assert gateway.upload(photo(), pid, "png", 40, 50) == response["secure_url"]
    for key, bad in [
        ("public_id", "foreign"),
        ("resource_type", "raw"),
        ("width", 999),
        ("format", "svg"),
        ("secure_url", "https://attacker.example/image.png"),
    ]:
        original = response[key]
        response[key] = bad
        with pytest.raises(AppError):
            gateway.upload(photo(), pid, "png", 40, 50)
        response[key] = original
