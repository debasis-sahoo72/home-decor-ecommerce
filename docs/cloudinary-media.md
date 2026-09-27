# Cloudinary product media

Open **Admin → Products → Edit → Product photographs**. Upload JPEG, PNG or WebP,
describe the actual product/view, set the primary image, move photos earlier or
later, replace one photo, or confirm deletion. Position zero is primary; position
one is the storefront hover view. All existing storefront frames remain 4:5.
Recommended source photography is 1200 × 1500 with four consistent product views.

## Setup

Put these values in `backend/.env` (not frontend environment files or Git):

```dotenv
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

From `backend`, install dependencies, migrate, and restart the backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

No unsigned upload preset is needed. Use a dedicated Cloudinary product environment
for this store. Do not change accounts while managed images or cleanup jobs still
belong to the old account. Public storefront photographs are public Cloudinary
assets; do not upload private documents or personal identity images.

## Validation and trust boundary

The browser sends the raw file to an authenticated, CSRF-protected admin endpoint.
The request limit is 5 MiB for this one upload path; normal JSON requests retain
the 16 KiB limit. Configure the production reverse proxy with equivalent request
limits and rate/concurrency controls before deployment.

Pillow identifies and fully decodes the file. Claimed MIME type must match the
decoded JPEG/PNG/WebP format. Empty, corrupt, animated, SVG and other formats are
rejected. Limits: 5 MiB input/output, 20 million pixels, 8000 pixels per side,
12 images per product. EXIF orientation is applied; re-encoding pixels removes
EXIF/GPS metadata and appended payloads. No image binary is written to PostgreSQL.

The backend generates a fresh public ID under `your-sanctuary/products/<product-id>/`.
It signs the Cloudinary Upload API request using SHA-256 and its server-only
secret; the browser never gets the signature, API key or secret. Provider replies
are checked for matching public ID, format, dimensions and HTTPS Cloudinary URL.
Provider error bodies are not exposed in errors or logs.

Stored data: public ID, secure versioned URL, width, height, format, byte size,
description, position and originating cloud name. Existing demo/external references
remain intact, with nullable new metadata. The obsolete arbitrary URL/metadata
write endpoints return 410; new assets must pass validated upload.

See Cloudinary's [Upload API reference](https://cloudinary.com/documentation/image_upload_api_reference)
and [authentication signatures](https://cloudinary.com/documentation/authentication_signatures).

## Replacement, ordering and deletion

Product row locks serialize media operations. Reordering must supply the exact
current image ID set, preventing cross-product images, duplicates and stale lists.
Two-phase position updates respect the existing unique position constraint.
Replacing keeps the image record ID and position, while assigning a new public ID
and versioned URL to avoid stale browser image caches. The old asset remains
associated until the replacement upload and database update both succeed.

Deletion first removes the association and compacts remaining positions, promoting
the next photo when necessary. Managed remote deletion is durably queued in the
small `media_cleanup` table and attempted by the editor; failures retain a retry
job. Cleanup requests Cloudinary CDN invalidation. Propagation can take time.
Legacy and local demo files are only detached, never remotely destroyed.

An upload cleanup intent is committed before calling Cloudinary. Failed uploads,
uncertain timeouts, crashes or failed database association therefore retain an
orphan cleanup job, eligible after an hour. Jobs are locked while uploading;
cleanup workers skip locked jobs and never delete a currently referenced asset.

For reliable unattended cleanup, run the following periodically using the deployment
scheduler (no Redis/queue infrastructure is required). Each run processes up to
20 due jobs; repeated failures back off up to one hour. The admin cleanup button
processes one due job. Monitor pending job count/attempts in production:

```powershell
.\.venv\Scripts\python.exe -m app.cli cleanup-media
```

Without the scheduler, pending jobs remain safe but require manual cleanup. Backups
restored after a remote deletion cannot restore that deleted Cloudinary asset;
configure Cloudinary backups separately if recovery is required.

## API

- `GET /api/v1/admin/media/config`: capability flags and limits, no credentials.
- `GET /api/v1/admin/products/{id}/media`: ordered metadata.
- `POST /api/v1/admin/products/{id}/media/upload?alt=...`: raw image body and actual
  MIME Content-Type; optional `replace_id` to replace that product's image.
- `PATCH /api/v1/admin/products/{id}/media/order`: `{ "image_ids": [...] }`.
- `PATCH /api/v1/admin/products/{id}/media/{image_id}`: `{ "alt": "..." }`.
- `DELETE /api/v1/admin/products/{id}/media/{image_id}`: remove and enqueue cleanup.
- `POST /api/v1/admin/media/cleanup`: attempt one due managed deletion.

Mutations require the normal session cookie, exact permitted Origin and CSRF token.

## Verification scope

Tests exercise decoding, size/pixel limits, forged types, animation, authorization,
CSRF, association, ordering, replacement rollback, cleanup retries and signed
provider requests using a mock HTTP transport. A real Cloudinary upload/delete
smoke test still requires configured credentials; it must not be represented as
verified when only mocks have run.
