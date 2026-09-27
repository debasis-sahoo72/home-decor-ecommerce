import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async headers() {
    const privatePaths = ["/admin/:path*", "/account/:path*", "/cart", "/wishlist", "/checkout", "/login", "/api/:path*"];
    return (process.env.SITE_INDEXABLE === "true" ? privatePaths : ["/:path*"]).map((source) => ({
      source, headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }],
    }));
  },
  async redirects() {
    return [{ source: "/products/:slug", destination: "/product/:slug", permanent: true }];
  },
  images: {
    localPatterns: [
      { pathname: "/demo/**" },
      { pathname: "/brand/**" },
    ],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "res.cloudinary.com",
        pathname: "/**/image/upload/**",
      },
      { protocol: "https", hostname: "images.unsplash.com" },
    ],
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
