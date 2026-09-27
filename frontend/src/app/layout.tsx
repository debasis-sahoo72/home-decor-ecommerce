import type { Metadata } from "next";
import "./globals.css";
import { ShoppingProvider } from "@/components/shopping-provider";
import { Header, Footer } from "@/components/shell";
import { siteSettings, defaultDescription } from "@/lib/seo";

export const metadata: Metadata = {
  metadataBase: new URL(siteSettings().origin),
  title: {
    default: "Your Sanctuary | Beautiful spaces. Happier living.",
    template: "%s | Your Sanctuary",
  },
  icons: { icon: "/brand/ys-monogram.png" },
  applicationName: "Your Sanctuary",
  description: defaultDescription,
  robots: { index: siteSettings().indexable, follow: true },
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
