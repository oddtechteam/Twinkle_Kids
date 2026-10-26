import type { MetadataRoute } from "next";

import { siteUrl } from "@/lib/site";

/** Personal and transactional pages stay out of search results (they also send noindex). */
export default function robots(): MetadataRoute.Robots {
  const base = siteUrl();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin", "/account", "/bag", "/wishlist", "/search", "/status", "/checkout", "/order-confirmation", "/api/"],
    },
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
