/**
 * Listing query model shared by server pages (parsing searchParams) and client controls
 * (building the next URL). The URL is the single source of truth for filters and sorting.
 */

import type { Money, ProductSort } from "@/lib/api/types";

export const SORT_OPTIONS: { value: ProductSort; label: string }[] = [
  { value: "featured", label: "Featured" },
  { value: "newest", label: "New arrivals" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "name_asc", label: "Name: A to Z" },
];

const SORTS = new Set<string>(SORT_OPTIONS.map((o) => o.value));
export const PAGE_SIZE = 24;

export interface ListingQuery {
  page: number;
  sort: ProductSort;
  /** Store default (CMS setting); omitted from URLs when selected. */
  defaultSort: ProductSort;
  q: string | null;
  /** Category / collection slugs chosen as filters on /shop (scoped pages ignore these). */
  category: string | null;
  collection: string | null;
  sizes: string[];
  colours: string[];
  minPrice: string | null;
  maxPrice: string | null;
  inStock: boolean;
}

export type SearchParamsRecord = Record<string, string | string[] | undefined>;

const MONEY = /^\d{1,10}(\.\d{1,2})?$/;
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function all(value: string | string[] | undefined): string[] {
  const list = Array.isArray(value) ? value : value ? [value] : [];
  return [...new Set(list.map((v) => v.trim()).filter(Boolean))].slice(0, 20);
}

export function parseListingQuery(
  params: SearchParamsRecord,
  defaultSort: ProductSort = "featured",
): ListingQuery {
  const page = Number.parseInt(first(params.page) ?? "1", 10);
  const sort = first(params.sort) ?? defaultSort;
  const q = first(params.q)?.trim().slice(0, 100) ?? "";
  const min = first(params.min_price) ?? "";
  const max = first(params.max_price) ?? "";
  const category = first(params.category)?.trim().toLowerCase() ?? "";
  const collection = first(params.collection)?.trim().toLowerCase() ?? "";
  return {
    page: Number.isFinite(page) && page > 0 ? Math.min(page, 10_000) : 1,
    sort: (SORTS.has(sort) ? sort : defaultSort) as ProductSort,
    defaultSort,
    q: q || null,
    category: SLUG.test(category) && category.length <= 160 ? category : null,
    collection: SLUG.test(collection) && collection.length <= 160 ? collection : null,
    sizes: all(params.size),
    colours: all(params.colour),
    minPrice: MONEY.test(min) ? min : null,
    maxPrice: MONEY.test(max) ? max : null,
    inStock: first(params.in_stock) === "true",
  };
}

/** API query string for GET /api/v1/products. */
export function toApiParams(
  query: ListingQuery,
  scope: { category?: string; collection?: string; pageSize?: number } = {},
): URLSearchParams {
  const params = new URLSearchParams();
  params.set("page", String(query.page));
  params.set("page_size", String(scope.pageSize ?? PAGE_SIZE));
  params.set("sort", query.sort);
  // A page's own scope (e.g. /category/[slug]) always wins over query-string filters.
  const category = scope.category ?? (scope.collection ? null : query.category);
  const collection = scope.collection ?? (scope.category ? null : query.collection);
  if (category) params.set("category", category);
  if (collection) params.set("collection", collection);
  if (query.q) params.set("q", query.q);
  if (query.minPrice) params.set("min_price", query.minPrice);
  if (query.maxPrice) params.set("max_price", query.maxPrice);
  if (query.inStock) params.set("in_stock", "true");
  query.sizes.forEach((s) => params.append("size", s));
  query.colours.forEach((c) => params.append("colour", c));
  return params;
}

/** Storefront URL for a listing with some fields changed. Filter changes reset to page 1. */
export function listingHref(
  basePath: string,
  query: ListingQuery,
  patch: Partial<ListingQuery> = {},
): string {
  const next: ListingQuery = { ...query, page: 1, ...patch };
  const params = new URLSearchParams();
  if (next.q) params.set("q", next.q);
  if (next.category) params.set("category", next.category);
  if (next.collection) params.set("collection", next.collection);
  if (next.sort !== next.defaultSort) params.set("sort", next.sort);
  next.sizes.forEach((s) => params.append("size", s));
  next.colours.forEach((c) => params.append("colour", c));
  if (next.minPrice) params.set("min_price", next.minPrice);
  if (next.maxPrice) params.set("max_price", next.maxPrice);
  if (next.inStock) params.set("in_stock", "true");
  if (next.page > 1) params.set("page", String(next.page));
  const search = params.toString();
  return search ? `${basePath}?${search}` : basePath;
}

export function toggleValue(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export function activeFilterCount(query: ListingQuery): number {
  return (
    (query.category ? 1 : 0) +
    (query.collection ? 1 : 0) +
    query.sizes.length +
    query.colours.length +
    (query.minPrice || query.maxPrice ? 1 : 0) +
    (query.inStock ? 1 : 0)
  );
}

/** Every filter cleared (search text and sort are kept). */
export const CLEARED_FILTERS: Partial<ListingQuery> = {
  category: null,
  collection: null,
  sizes: [],
  colours: [],
  minPrice: null,
  maxPrice: null,
  inStock: false,
};

export interface PriceBand {
  label: string;
  min: string | null;
  max: string | null;
}

const NICE_STEPS = [100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000];

/**
 * Up to four price bands spanning the live catalogue range (GET /products/facets), rounded to
 * friendly amounts — so no price list is ever hardcoded and empty bands are avoided.
 */
export function priceBands(minPrice: Money | null, maxPrice: Money | null, format: (value: string) => string): PriceBand[] {
  const low = Number(minPrice);
  const high = Number(maxPrice);
  if (!Number.isFinite(low) || !Number.isFinite(high) || high <= low) return [];
  const step = NICE_STEPS.find((s) => (high - low) / s <= 4) ?? NICE_STEPS[NICE_STEPS.length - 1]!;
  const edges: number[] = [];
  for (let edge = Math.ceil((low + 1) / step) * step; edge < high && edges.length < 3; edge += step) edges.push(edge);
  if (edges.length === 0) return [];

  const bands: PriceBand[] = [];
  bands.push({ label: `Under ${format(String(edges[0]))}`, min: null, max: (edges[0]! - 0.01).toFixed(2) });
  for (let i = 1; i < edges.length; i++) {
    bands.push({
      label: `${format(String(edges[i - 1]))} – ${format(String(edges[i]! - 1))}`,
      min: String(edges[i - 1]),
      max: (edges[i]! - 0.01).toFixed(2),
    });
  }
  const last = edges[edges.length - 1]!;
  bands.push({ label: `${format(String(last))} & above`, min: String(last), max: null });
  return bands;
}
