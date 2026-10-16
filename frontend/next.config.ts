import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  images: {
    // Storefront media lives in Neon Object Storage's public `media` bucket, served from the
    // branch endpoint (<branch-id>.storage.<cell>.<region>.aws.neon.tech/media/...).
    // Only that bucket is allowed; private buckets are never rendered via next/image.
    remotePatterns: [{ protocol: "https", hostname: "**.aws.neon.tech", pathname: "/media/**" }],
  },
};

export default nextConfig;
