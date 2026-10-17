/**
 * Listing query model shared by server pages (parsing searchParams) and client controls
 * (building the next URL). The URL is the single source of truth for filters and sorting.
 */

import type { ProductSort } from "@/lib/api/types";

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
  sizes: string[];
  colours: string[];
  minPrice: string | null;
  maxPrice: string | null;
  inStock: boolean;
}

export type SearchParamsRecord = Record<string, string | string[] | undefined>;

const MONEY = /^\d{1,10}(\.\d{1,2})?$/;

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
  return {
    page: Number.isFinite(page) && page > 0 ? Math.min(page, 10_000) : 1,
    sort: (SORTS.has(sort) ? sort : defaultSort) as ProductSort,
    defaultSort,
    q: q || null,
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
  if (scope.category) params.set("category", scope.category);
  if (scope.collection) params.set("collection", scope.collection);
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
    query.sizes.length +
    query.colours.length +
    (query.minPrice || query.maxPrice ? 1 : 0) +
    (query.inStock ? 1 : 0)
  );
}
