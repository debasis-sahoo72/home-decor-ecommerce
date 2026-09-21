"use client";
import Image from "next/image";
import { useState } from "react";
import type { Product } from "@/lib/catalog";
export default function ProductGallery({
  images,
  name,
}: {
  images: Product["images"];
  name: string;
}) {
  const [selected, setSelected] = useState(0);
  const image = images[selected] || images[0];
  if (!image)
    return (
      <div className="gallery-main photo-placeholder">
        Photography for {name} is coming soon.
      </div>
    );
  return (
    <section className="gallery" aria-label={`${name} image gallery`}>
      <div className="gallery-main">
        <Image
          src={image.url}
          alt={image.alt.trim() || `${name} product view ${selected + 1}`}
          fill
          sizes="(max-width:768px) 90vw, 52vw"
          preload={selected === 0}
        />
      </div>
      {images.length > 1 && (
        <div className="gallery-thumbnails" aria-label="Choose a product image">
          {images.map((i, index) => (
            <button
              key={i.id}
              type="button"
              className="gallery-thumb"
              onClick={() => setSelected(index)}
              aria-pressed={selected === index}
              aria-label={`View image ${index + 1}: ${i.alt.trim() || name}`}
            >
              <Image src={i.url} alt="" fill sizes="80px" />
            </button>
          ))}
        </div>
      )}
      <p className="muted" aria-live="polite">
        Image {selected + 1} of {images.length}
      </p>
    </section>
  );
}
