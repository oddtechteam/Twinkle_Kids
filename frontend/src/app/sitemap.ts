import type { MetadataRoute } from "next";
import { connection } from "next/server";

import { getSitemap } from "@/lib/catalog/api";
import { siteUrl } from "@/lib/site";

/**
 * Public, indexable URLs only: active products and categories, published collections and
 * pages (the API filters drafts). Rendered per request so new products appear immediately and
 * a build without API access never bakes in an empty sitemap.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  await connection();
  const base = siteUrl();
  const result = await getSitemap();
  const fixed: MetadataRoute.Sitemap = [
    { url: `${base}/`, changeFrequency: "daily", priority: 1 },
    { url: `${base}/shop`, changeFrequency: "daily", priority: 0.9 },
    { url: `${base}/about`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${base}/contact`, changeFrequency: "monthly", priority: 0.4 },
  ];
  if (!result.ok) return fixed;

  const entry = (path: string, updated: string | null, priority: number): MetadataRoute.Sitemap[number] => ({
    url: `${base}${path}`,
    lastModified: updated ?? undefined,
    priority,
  });
  const { products, categories, collections, pages } = result.data;
  return [
    ...fixed,
    ...categories.map((c) => entry(`/category/${c.slug}`, c.updated_at, 0.8)),
    ...collections.map((c) => entry(`/collections/${c.slug}`, c.updated_at, 0.7)),
    ...products.map((p) => entry(`/products/${p.slug}`, p.updated_at, 0.8)),
    ...pages.map((p) => entry(`/pages/${p.slug}`, p.updated_at, 0.3)),
  ];
}
