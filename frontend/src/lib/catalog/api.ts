/**
 * Typed catalogue data access (server components). All storefront catalogue reads go through
 * here — presentation components never call fetch directly.
 *
 * Reads are uncached request-time data, so callers render them inside <Suspense>. When CDN
 * caching is introduced, add "use cache" + cacheLife/cacheTag in this file only.
 */

import "server-only";

import { ApiError, apiFetch } from "@/lib/api/client";
import type {
  ApiResult,
  Category,
  CategoryDetail,
  CollectionSummary,
  Facets,
  ProductDetail,
  ProductList,
  ProductSort,
  Recommendations,
  ReviewSummary,
  ShippingRule,
  Sitemap,
} from "@/lib/api/types";
import { type ListingQuery, toApiParams } from "./query";

async function attempt<T>(path: string): Promise<ApiResult<T>> {
  try {
    const data = await apiFetch<T>(path, { cache: "no-store" });
    return { ok: true, data };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, status: error.status, message: error.message };
    }
    return { ok: false, status: 503, message: "The catalogue is temporarily unavailable." };
  }
}

export function listProducts(
  query: ListingQuery,
  scope: { category?: string; collection?: string; pageSize?: number } = {},
): Promise<ApiResult<ProductList>> {
  return attempt<ProductList>(`/products?${toApiParams(query, scope).toString()}`);
}

/** Small product selections for homepage rails and related products. */
export function selectProducts(selection: {
  sort?: ProductSort;
  category?: string;
  collection?: string;
  limit?: number;
}): Promise<ApiResult<ProductList>> {
  const params = new URLSearchParams({
    page: "1",
    page_size: String(Math.min(selection.limit ?? 8, 60)),
    sort: selection.sort ?? "featured",
  });
  if (selection.category) params.set("category", selection.category);
  if (selection.collection) params.set("collection", selection.collection);
  return attempt<ProductList>(`/products?${params.toString()}`);
}

export function getProduct(slug: string): Promise<ApiResult<ProductDetail>> {
  return attempt<ProductDetail>(`/products/${encodeURIComponent(slug)}`);
}

export function listCategories(): Promise<ApiResult<Category[]>> {
  return attempt<Category[]>("/categories");
}

export function getCategory(slug: string): Promise<ApiResult<CategoryDetail>> {
  // Only the category header is needed here; products are listed via listProducts + filters.
  return attempt<CategoryDetail>(`/categories/${encodeURIComponent(slug)}?page_size=1`);
}

export function topLevel(categories: Category[]): Category[] {
  return categories
    .filter((c) => c.parent_id === null)
    .sort((a, b) => a.display_order - b.display_order || a.name.localeCompare(b.name));
}

export type CollectionInfo = CollectionSummary;

/** Published collection details (404 for drafts or unknown slugs). */
export function getCollection(slug: string): Promise<ApiResult<CollectionInfo>> {
  return attempt<CollectionInfo>(`/collections/${encodeURIComponent(slug)}`);
}

/** Published collections in display order (filters, navigation fallbacks). */
export function listCollections(): Promise<ApiResult<CollectionSummary[]>> {
  return attempt<CollectionSummary[]>("/collections");
}

/** Size / colour / price options for a listing scope, computed server-side. */
export function getFacets(scope: { category?: string; collection?: string; q?: string | null }): Promise<ApiResult<Facets>> {
  const params = new URLSearchParams();
  if (scope.category) params.set("category", scope.category);
  if (scope.collection) params.set("collection", scope.collection);
  if (scope.q) params.set("q", scope.q);
  return attempt<Facets>(`/products/facets?${params.toString()}`);
}

/** Approved reviews for a product (empty when none have been approved). */
export function getReviews(slug: string): Promise<ApiResult<ReviewSummary>> {
  return attempt<ReviewSummary>(`/products/${encodeURIComponent(slug)}/reviews`);
}

export function getRecommendations(slug: string): Promise<ApiResult<Recommendations>> {
  return attempt<Recommendations>(`/products/${encodeURIComponent(slug)}/recommendations`);
}

/** Active delivery fee bands from store settings. */
export function getShippingRules(): Promise<ApiResult<ShippingRule[]>> {
  return attempt<ShippingRule[]>("/content/shipping");
}

/** Public, indexable slugs for the sitemap. */
export function getSitemap(): Promise<ApiResult<Sitemap>> {
  return attempt<Sitemap>("/sitemap");
}
