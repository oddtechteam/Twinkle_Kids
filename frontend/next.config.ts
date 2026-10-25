import type { NextConfig } from "next";

const API_ORIGIN = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");

/** Optional CDN origin for public media (MEDIA_PUBLIC_BASE_URL), allowed alongside Neon storage. */
function mediaCdnPattern() {
  const raw = process.env.MEDIA_PUBLIC_BASE_URL;
  if (!raw) return [];
  try {
    const url = new URL(raw);
    const path = url.pathname.replace(/\/+$/, "");
    return [{ protocol: url.protocol.replace(":", "") as "http" | "https", hostname: url.hostname, pathname: `${path}/**` }];
  } catch {
    return [];
  }
}

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  images: {
    // Storefront media lives in Neon Object Storage's public `media` bucket, served from the
    // branch endpoint (<branch-id>.storage.<cell>.<region>.aws.neon.tech/media/...).
    // Only that bucket is allowed; private buckets are never rendered via next/image.
    remotePatterns: [{ protocol: "https", hostname: "**.aws.neon.tech", pathname: "/media/**" }, ...mediaCdnPattern()],
  },
  async rewrites() {
    // Browser → same-origin /api/v1/* → FastAPI. Keeps session/CSRF cookies first-party and
    // the API origin out of client bundles.
    return [{ source: "/api/v1/:path*", destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
};

export default nextConfig;
