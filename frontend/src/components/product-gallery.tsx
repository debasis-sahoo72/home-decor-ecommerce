"use client";
import Image from "next/image";
import { useState } from "react";
import type { Product } from "@/lib/catalog";
import { imageSource, productName } from "@/lib/media";
export default function ProductGallery({
  images,
  name,
}: {
  images: Product["images"];
  name: string;
}) {
  const [selected, setSelected] = useState(0);
  const [zoomed, setZoomed] = useState(false);
  const image = images[selected] || images[0];
  function choose(index: number) {
    setSelected((index + images.length) % images.length);
    setZoomed(false);
  }
  if (!image)
    return (
      <div className="gallery-main photo-placeholder">
        Photography for {productName(name)} is coming soon.
      </div>
    );
  return (
    <section
      className="gallery"
      aria-label={`${productName(name)} image gallery`}
    >
      <button
        type="button"
        className={`gallery-main ${zoomed ? "is-zoomed" : ""}`}
        onClick={() => setZoomed(!zoomed)}
        aria-pressed={zoomed}
        aria-label={zoomed ? "Zoom out product image" : "Zoom in product image"}
      >
        <Image
          key={image.id}
          src={imageSource(image.url)}
          alt={
            image.alt.trim() ||
            `${productName(name)} product view ${selected + 1}`
          }
          fill
          sizes="(max-width:768px) 90vw, 45vw"
          preload={selected === 0}
        />
        <span className="zoom-hint">
          {zoomed ? "− Zoom out" : "+ Take a closer look"}
        </span>
      </button>
      {images.length > 1 && (
        <div
          className="gallery-thumbnails"
          aria-label="Choose a product image"
          onKeyDown={(event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
              event.preventDefault();
              const next =
                (selected +
                  (event.key === "ArrowRight" ? 1 : -1) +
                  images.length) %
                images.length;
              choose(next);
              const buttons = event.currentTarget.querySelectorAll("button");
              buttons[next]?.focus();
            }
          }}
        >
          {images.map((i, index) => (
            <button
              key={i.id}
              type="button"
              className="gallery-thumb"
              onClick={() => choose(index)}
              aria-pressed={selected === index}
              aria-label={`View image ${index + 1}: ${i.alt.trim() || productName(name)}`}
            >
              <Image src={imageSource(i.url)} alt="" fill sizes="80px" />
            </button>
          ))}
        </div>
      )}
      <div className="gallery-controls">
        <button
          type="button"
          onClick={() => choose(selected - 1)}
          disabled={images.length < 2}
          aria-label="Previous product image"
        >
          ←
        </button>
        <p className="muted" aria-live="polite">
          Image {selected + 1} of {images.length}
        </p>
        <button
          type="button"
          onClick={() => choose(selected + 1)}
          disabled={images.length < 2}
          aria-label="Next product image"
        >
          →
        </button>
      </div>
    </section>
  );
}
