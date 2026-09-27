import Image from "next/image";
import Link from "next/link";
import { money, Product } from "@/lib/catalog";
import WishlistButton from "./wishlist-button";
import { imageSource, isDemo, productName } from "@/lib/media";
export default function ProductCard({ product: p }: { product: Product }) {
  const v = p.variants[0];
  const image = p.images[0];
  return (
    <article className="product-card">
      <div className="product-picture">
        <Link href={`/product/${p.slug}`} tabIndex={-1} aria-hidden="true">
          {image ? (
            <Image
              src={imageSource(image.url)}
              alt={image.alt || productName(p.name)}
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            />
          ) : (
            <span className="photo-placeholder">Photography coming soon</span>
          )}
        </Link>
        {p.images[1] && (
          <Image
            className="product-hover-image"
            src={imageSource(p.images[1].url)}
            alt=""
            fill
            sizes="(max-width: 640px) 50vw, 30vw"
          />
        )}
        <Link className="product-quick-link" href={`/product/${p.slug}`}>
          Discover this piece <span aria-hidden="true">→</span>
        </Link>
        <WishlistButton id={p.id} name={p.name} />
        {isDemo(p.name) && <span className="demo-badge">Demo</span>}
        {v?.discount_percent > 0 && (
          <span className="sale-badge">{v.discount_percent}% off</span>
        )}
      </div>
      <p className="eyebrow">{p.category.name}</p>
      <h3>
        <Link href={`/product/${p.slug}`}>{productName(p.name)}</Link>
      </h3>
      <p className="price">
        {p.price ? (
          <>
            {p.variants.length > 1 && "From "}
            {money(p.price)}
          </>
        ) : (
          "Price coming soon"
        )}{" "}
        {v?.compare_at_price && v.discount_percent > 0 && (
          <del>{money(v.compare_at_price)}</del>
        )}
      </p>
      {p.review_count > 0 && (
        <p className="muted">
          ★ {p.rating} · {p.review_count} reviews
        </p>
      )}
      {!p.in_stock && <p className="stock-note">Currently out of stock</p>}
    </article>
  );
}
