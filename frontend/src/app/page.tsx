import Image from "next/image";
import Link from "next/link";
import { api, Category, ProductPage } from "@/lib/catalog";
import { imageSource } from "@/lib/media";
import ProductGrid from "@/components/product-grid";
import Icon from "@/components/icon";
export const metadata = { alternates: { canonical: "/" } };
export default async function Home() {
  const [categories, arrivals, featured] = await Promise.allSettled([
    api<Category[]>("/categories"),
    api<ProductPage>("/products?sort=newest&page_size=8"),
    api<ProductPage>("/products?featured=true&page_size=4"),
  ]);
  const items = arrivals.status === "fulfilled" ? arrivals.value.items : [];
  const picks = featured.status === "fulfilled" ? featured.value.items : [];
  return (
    <>
      <section className="premium-hero">
        <Image
          src="/demo/hero.png?v=20260923"
          alt="Ivory vases with olive branches on an oak console in a sunlit neutral home"
          fill
          preload
          loading="eager"
          sizes="100vw"
        />
        <div className="wrap hero-content">
          <p className="eyebrow">The art of feeling at home</p>
          <h1>
            Beautiful spaces.
            <br />
            Happier living.
          </h1>
          <p>
            Thoughtful pieces. Natural textures.
            <br />A little everyday beauty, made yours.
          </p>
          <Link className="button button-primary" href="/shop">
            Shop the collection <Icon name="arrow" />
          </Link>
          <span className="hero-note">Small details. A whole new feeling.</span>
        </div>
        <span className="hero-edition">THE CONSIDERED HOME / 01</span>
      </section>
      <div className="service-strip wrap">
        <div>
          <Icon name="truck" />
          <span>
            <strong>Find your delivery</strong>
            <small>Check availability by PIN code</small>
          </span>
        </div>
        <div>
          <Icon name="leaf" />
          <span>
            <strong>A considered collection</strong>
            <small>Details for every corner</small>
          </span>
        </div>
        <div>
          <Icon name="heart" />
          <span>
            <strong>Save what you love</strong>
            <small>Build your personal wishlist</small>
          </span>
        </div>
        <div>
          <Icon name="sparkle" />
          <span>
            <strong>Look a little closer</strong>
            <small>Materials, textures & more</small>
          </span>
        </div>
      </div>
      <section className="section wrap">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Find your inspiration</p>
            <h2>Shop by category</h2>
          </div>
          <Link href="/shop">
            View all <span aria-hidden="true">→</span>
          </Link>
        </div>
        {categories.status === "fulfilled" && categories.value.length ? (
          <div className="photo-categories">
            {categories.value.map((c) => {
              const product = items.find((p) => p.category.id === c.id);
              const source = product?.images[0];
              return (
                <Link
                  href={`/categories/${c.slug}`}
                  key={c.id}
                  className="photo-category"
                >
                  <div>
                    {source ? (
                      <Image
                        src={imageSource(source.url)}
                        alt={source.alt}
                        fill
                        sizes="(max-width:640px) 45vw, 30vw"
                      />
                    ) : (
                      <span className="photo-placeholder">
                        Explore the collection
                      </span>
                    )}
                    <span className="category-arrow">
                      <Icon name="arrow" />
                    </span>
                  </div>
                  <h3>{c.name}</h3>
                  <p>Discover your next favourite</p>
                </Link>
              );
            })}
          </div>
        ) : (
          <p className="empty-note">
            {categories.status === "rejected"
              ? "Our collections are temporarily unavailable. Please try again shortly."
              : "Our collections are taking shape. Please check back shortly."}
          </p>
        )}
      </section>
      <section className="section wrap arrivals-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">A fresh perspective</p>
            <h2>New arrivals, timeless appeal</h2>
          </div>
          <Link href="/shop?sort=newest">Shop new arrivals →</Link>
        </div>
        {items.length ? (
          <ProductGrid products={items.slice(0, 4)} />
        ) : (
          <div className="empty-note">
            {arrivals.status === "rejected"
              ? "The collection could not be loaded. Visit the shop to try again."
              : "Our newest pieces will appear here."}
            <Link href="/shop">Explore the shop →</Link>
          </div>
        )}
      </section>
      <section className="collection-banner wrap">
        <Image
          src="/demo/hero.png?v=20260923"
          alt="Warm oak, natural textures and sculptural vases for a considered home"
          fill
          sizes="90vw"
        />
        <div>
          <p className="eyebrow">Little changes. Lovely spaces.</p>
          <h2>
            Turn a house
            <br />
            into your home.
          </h2>
          <p>Find beauty in the everyday.</p>
          <Link className="button button-primary" href="/shop?featured=true">
            Explore the edit <Icon name="arrow" />
          </Link>
        </div>
      </section>
      {picks.length > 0 && (
        <section className="section wrap">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Selected with a little extra care</p>
              <h2>The considered edit</h2>
            </div>
            <Link href="/shop?featured=true">View the edit →</Link>
          </div>
          <ProductGrid products={picks} />
        </section>
      )}
      <section className="inspiration-band">
        <div className="wrap">
          <Icon name="leaf" />
          <p className="eyebrow">Make room for what matters</p>
          <h2>
            A softer light. A warmer corner.
            <br />A home that feels like you.
          </h2>
          <Link href="/shop" className="text-link">
            Find your finishing touch →
          </Link>
        </div>
      </section>
    </>
  );
}
