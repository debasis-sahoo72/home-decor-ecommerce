"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import { imageSource } from "@/lib/media";
import { readApi } from "@/lib/orders";
import { request } from "@/lib/shopping-client";

type Media = {
  id: string;
  url: string;
  alt: string;
  position: number;
  width: number;
  height: number;
  byte_size: number | null;
  format: string | null;
  managed: boolean;
};
type Config = {
  enabled: boolean;
  max_bytes: number;
  max_images: number;
  formats: string[];
};

export default function ProductMedia({ productId }: { productId: string }) {
  const [images, setImages] = useState<Media[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [replace, setReplace] = useState<Media | null>(null);
  const [deleting, setDeleting] = useState("");
  const [revision, setRevision] = useState(0);
  const base = `/admin/products/${productId}/media`;
  useEffect(() => {
    const c = new AbortController();
    Promise.all([
      readApi<Media[]>(base, c.signal),
      readApi<Config>("/admin/media/config", c.signal),
    ])
      .then(([rows, settings]) => {
        if (!c.signal.aborted) {
          setImages(rows);
          setConfig(settings);
          setError("");
        }
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [base, revision]);
  async function action(fn: () => Promise<Media[]>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      setImages(await fn());
      setReplace(null);
      setDeleting("");
      setNotice(
        "Images saved. Removed Cloudinary assets are queued for cleanup.",
      );
      if (config?.enabled) {
        // The image change is already committed. Cleanup failure must not undo its UI result.
        try {
          const result = await request<{pending_retry: number}>("/admin/media/cleanup");
          setNotice(result.pending_retry ? "Images saved. Cloudinary cleanup will retry later." : "Images saved. Pending cleanup checked.");
        } catch {
          setNotice("Images saved. Cloudinary cleanup is pending; use the cleanup control to retry.");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save images.");
    } finally {
      setBusy(false);
    }
  }
  function move(id: string, to: number) {
    const ordered = images.filter((i) => i.id !== id);
    ordered.splice(
      to,
      0,
      images.find((i) => i.id === id)!,
    );
    void action(() =>
      request(
        base + "/order",
        { image_ids: ordered.map((i) => i.id) },
        "PATCH",
      ),
    );
  }
  return (
    <section className="product-media" aria-label="Product image management">
      <h3>Product photographs</h3>
      <p>
        Use four views: front, alternate angle, detail and styled setting.
        Images use the same 4:5 frame throughout the shop. Recommended source
        size: 1200 × 1500 pixels.
      </p>
      <p role="alert" className="ops-error">
        {error}
      </p>
      <p role="status">{notice}</p>
      {loading ? (
        <p role="status">Loading images…</p>
      ) : (
        <>
          {!config && (
            <button type="button" onClick={() => setRevision((v) => v + 1)}>
              Retry loading images
            </button>
          )}
          {config && !config.enabled && (
            <p className="empty-note">
              Uploads require Cloudinary configuration on the backend. You can
              still describe, reorder and remove existing images.
            </p>
          )}
          <div className="media-grid">
            {images.map((im, n) => (
              <article className="ops-card" key={im.id}>
                <div className="media-preview">
                  <Image
                    src={imageSource(im.url)}
                    alt={im.alt}
                    fill
                    sizes="(max-width: 600px) 90vw, 280px"
                  />
                </div>
                <p>
                  <strong>
                    {n === 0 ? "Primary image" : `Image ${n + 1}`}
                  </strong>{" "}
                  · {im.width} × {im.height}
                  {im.format && ` · ${im.format.toUpperCase()}`}
                </p>
                <form
                  className="ops-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    void action(() =>
                      request(
                        `${base}/${im.id}`,
                        { alt: f.get("alt") },
                        "PATCH",
                      ),
                    );
                  }}
                >
                  <label className="wide">
                    Image description
                    <input
                      name="alt"
                      key={im.alt}
                      defaultValue={im.alt}
                      required
                      maxLength={300}
                    />
                  </label>
                  <button className="text-button" disabled={busy}>
                    Save description
                  </button>
                </form>
                <div className="ops-actions">
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy || n === 0}
                    onClick={() => move(im.id, 0)}
                  >
                    Make primary
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    aria-label={`Move image ${n + 1} earlier`}
                    disabled={busy || n === 0}
                    onClick={() => move(im.id, n - 1)}
                  >
                    Move earlier
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    aria-label={`Move image ${n + 1} later`}
                    disabled={busy || n === images.length - 1}
                    onClick={() => move(im.id, n + 1)}
                  >
                    Move later
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy || !config?.enabled}
                    onClick={() => setReplace(im)}
                  >
                    Replace image {n + 1}
                  </button>
                  <button
                    type="button"
                    className="text-button"
                    disabled={busy}
                    onClick={() => setDeleting(im.id)}
                  >
                    Delete image {n + 1}
                  </button>
                </div>
                {deleting === im.id && (
                  <div role="group" aria-label="Confirm image deletion">
                    <p>
                      Remove this photo from the product? Managed Cloudinary
                      assets will also be deleted.
                    </p>
                    <button
                      className="button button-secondary"
                      disabled={busy}
                      onClick={() =>
                        void action(() =>
                          request(`${base}/${im.id}`, undefined, "DELETE"),
                        )
                      }
                    >
                      Confirm delete
                    </button>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => setDeleting("")}
                    >
                      Keep image
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
          {!images.length && (
            <p className="empty-note">
              No product images yet. Upload your first photograph to make it the
              primary image.
            </p>
          )}
          <form
            className="ops-form ops-card"
            key={replace?.id || `new-${images.length}`}
            onSubmit={(e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const f = new FormData(form);
              const file = f.get("file");
              if (!(file instanceof File) || !file.size || !config) return;
              if (
                file.size > config.max_bytes ||
                !config.formats.includes(file.type)
              ) {
                setError("Choose a JPEG, PNG or WebP image up to 5 MB.");
                return;
              }
              void action(async () => {
                const csrf = await readApi<{ csrf_token: string }>(
                  "/auth/csrf",
                );
                const params = new URLSearchParams({
                  alt: String(f.get("alt") || ""),
                });
                if (replace) params.set("replace_id", replace.id);
                const response = await fetch(
                  `/api/v1${base}/upload?${params}`,
                  {
                    method: "POST",
                    headers: {
                      "Content-Type": file.type,
                      "X-CSRF-Token": csrf.csrf_token,
                    },
                    body: file,
                  },
                );
                const result = await response.json();
                if (!response.ok)
                  throw new Error(
                    result?.error?.message || "Upload failed. Please retry.",
                  );
                form.reset();
                return result;
              });
            }}
          >
            <h3 className="wide">
              {replace
                ? `Replace image ${replace.position + 1}`
                : "Upload a photograph"}
            </h3>
            <label className="wide">
              JPEG, PNG or WebP · maximum 5 MB
              <input
                type="file"
                name="file"
                accept="image/jpeg,image/png,image/webp"
                required
                disabled={busy || !config?.enabled}
              />
            </label>
            <label className="wide">
              Meaningful image description
              <input
                name="alt"
                defaultValue={replace?.alt || ""}
                maxLength={300}
                required
                disabled={busy || !config?.enabled}
              />
            </label>
            <p className="wide muted">
              Static images only, up to 20 megapixels and 8000 pixels per side.
              The server checks actual image content and removes embedded
              metadata.
            </p>
            <button
              className="button button-primary"
              disabled={
                busy ||
                !config?.enabled ||
                (!replace && images.length >= config.max_images)
              }
            >
              {busy
                ? "Saving…"
                : replace
                  ? "Upload replacement"
                  : "Upload image"}
            </button>
            {replace && (
              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() => setReplace(null)}
              >
                Cancel replacement
              </button>
            )}
          </form>
          {config?.enabled && (
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const result = await request<{
                    deleted: number;
                    pending_retry: number;
                  }>("/admin/media/cleanup");
                  setNotice(
                    `${result.deleted} removed assets cleaned up. ${result.pending_retry} awaiting retry.`,
                  );
                } catch (e) {
                  setError(
                    e instanceof Error ? e.message : "Cleanup is pending.",
                  );
                } finally {
                  setBusy(false);
                }
              }}
            >
              Run pending Cloudinary cleanup
            </button>
          )}
        </>
      )}
    </section>
  );
}
