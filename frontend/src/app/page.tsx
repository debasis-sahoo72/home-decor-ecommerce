export default function Home() {
  return (
    <main className="min-h-screen bg-stone-50 px-6 py-24 text-stone-900">
      <section className="mx-auto max-w-2xl rounded-2xl border border-stone-200 bg-white p-10">
        <p className="text-sm font-semibold uppercase tracking-widest text-stone-500">Development environment</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight">Home Decor</h1>
        <p className="mt-5 leading-7 text-stone-600">The project foundation is ready. Storefront and admin features will be added in later phases.</p>
        <a className="mt-8 inline-block rounded-lg bg-stone-900 px-5 py-3 text-white focus-visible:outline-2 focus-visible:outline-offset-4" href="/api/v1/health">Check API health</a>
      </section>
    </main>
  );
}
