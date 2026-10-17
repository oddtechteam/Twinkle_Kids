import type { NextConfig } from "next";

const API_ORIGIN = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  images: {
    // Storefront media lives in Neon Object Storage's public `media` bucket, served from the
    // branch endpoint (<branch-id>.storage.<cell>.<region>.aws.neon.tech/media/...).
    // Only that bucket is allowed; private buckets are never rendered via next/image.
    remotePatterns: [{ protocol: "https", hostname: "**.aws.neon.tech", pathname: "/media/**" }],
  },
  async rewrites() {
    // Browser → same-origin /api/v1/* → FastAPI. Keeps session/CSRF cookies first-party and
    // the API origin out of client bundles.
    return [{ source: "/api/v1/:path*", destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
};

export default nextConfig;
