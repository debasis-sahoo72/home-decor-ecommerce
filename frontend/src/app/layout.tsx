import type { Metadata } from "next";
import "./globals.css";
import { ShoppingProvider } from "@/components/shopping-provider";
import { Header, Footer } from "@/components/shell";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.SITE_URL || "http://127.0.0.1:3000"),
  title: {
    default: "Home Decor | A home, a little more you",
    template: "%s | Home Decor",
  },
  description:
    "Explore warm textures, considered lighting and beautiful everyday objects for your home.",
  robots: { index: process.env.SITE_INDEXABLE === "true", follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-IN">
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <ShoppingProvider>
          <Header />
          <main id="main">{children}</main>
          <Footer />
        </ShoppingProvider>
      </body>
    </html>
  );
}
