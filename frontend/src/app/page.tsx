import Image from "next/image";
import Link from "next/link";
import { api, Category, ProductPage, photos } from "@/lib/catalog";
import ProductGrid from "@/components/product-grid";
export const metadata = { alternates: { canonical: "/" } };
export default async function Home() {
  const [categories, arrivals, best] = await Promise.allSettled([
    api<Category[]>("/categories"),
    api<ProductPage>("/products?page_size=4"),
    api<ProductPage>("/products?sort=best_sellers&page_size=4"),
  ]);
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Objects for a life well lived</p>
          <h1>
            A home.
            <br />A little more <em>you.</em>
          </h1>
          <p>
            Quiet textures. Warm corners. Pieces that make the everyday feel a
            little more special.
          </p>
          <Link className="button button-primary" href="/shop">
            Find your next favourite <span aria-hidden="true">↗</span>
          </Link>
          <span className="hero-note">
            Considered details. Everyday beauty.
          </span>
        </div>
        <div className="hero-photo">
          <Image
            src={photos.room}
            alt="A sunlit living room with soft neutral seating, natural textures and warm wood"
            fill
            preload
            sizes="(max-width: 768px) 100vw, 60vw"
          />
          <span className="photo-caption">A softer kind of everyday.</span>
        </div>
      </section>
      <section className="section wrap">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Start with a little inspiration</p>
            <h2>What feels like home?</h2>
          </div>
          <Link href="/shop">Explore everything ↗</Link>
        </div>
        {categories.status === "fulfilled" && categories.value.length > 0 ? (
          <div className="category-grid">
            {categories.value.map((c, i) => (
              <Link
                href={`/categories/${c.slug}`}
                className={`category-tile tone-${i % 3}`}
                key={c.id}
              >
                <span aria-hidden="true" className="category-number">
                  0{i + 1}
                </span>
                <h3>{c.name}</h3>
                <span>Explore collection ↗</span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="empty-note">
            {categories.status === "rejected"
              ? "Our collections are temporarily unavailable. Please try again shortly."
              : "Our first collections are taking shape. Check back soon."}
          </p>
        )}
      </section>
      <section className="section wrap">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Fresh perspectives</p>
            <h2>New to the collection</h2>
          </div>
          <Link href="/shop?sort=newest">View new arrivals ↗</Link>
        </div>
        {arrivals.status === "fulfilled" && arrivals.value.items.length ? (
          <ProductGrid products={arrivals.value.items} />
        ) : (
          <div className="empty-note">
            {arrivals.status === "rejected"
              ? "We could not load the collection right now. Please visit the shop to try again."
              : "Good things are on their way. Our first pieces will appear here as they arrive."}
            <Link href="/shop">Explore the shop ↗</Link>
          </div>
        )}
      </section>
      <section className="editorial">
        <div className="editorial-photo">
          <Image
            src={photos.detail}
            alt="Warm wood and natural tones in a calm contemporary interior"
            fill
            sizes="(max-width: 768px) 100vw, 50vw"
          />
        </div>
        <div className="editorial-copy">
          <p className="eyebrow">The considered home</p>
          <h2>
            Less rush.
            <br />
            More room to unwind.
          </h2>
          <p>
            Bring together a tactile throw, a gentle pool of light and an object
            you love. Sometimes, a small change makes all the difference.
          </p>
          <Link className="button button-secondary" href="/shop?featured=true">
            Discover the edit ↗
          </Link>
        </div>
      </section>
      {best.status === "fulfilled" && best.value.items.length > 0 && (
        <section className="section wrap">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Chosen for real homes</p>
              <h2>Best sellers</h2>
            </div>
            <Link href="/shop?sort=best_sellers">View best sellers ↗</Link>
          </div>
          <ProductGrid products={best.value.items} />
        </section>
      )}
      <section className="section wrap values">
        <div>
          <span className="eyebrow">01 / A considered collection</span>
          <h3>Room for your own style.</h3>
          <p>Explore lighting, textiles and decor objects in one place.</p>
        </div>
        <div>
          <span className="eyebrow">02 / Details that matter</span>
          <h3>Look a little closer.</h3>
          <p>
            Find dimensions, materials and available variants on each product.
          </p>
        </div>
        <div>
          <span className="eyebrow">03 / Take your time</span>
          <h3>Keep what catches your eye.</h3>
          <p>
            Save your favourite pieces on this device and come back when
            inspiration strikes.
          </p>
        </div>
      </section>
    </>
  );
}
