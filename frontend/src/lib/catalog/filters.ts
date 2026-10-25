import type { ApiResult, Category, CollectionSummary, Facets } from "@/lib/api/types";
import { formatMoney } from "@/lib/format";
import { type PriceBand, priceBands } from "./query";

/** Everything a filter panel can offer — all of it derived from live catalogue data. */
export interface FilterOptions {
  sizes: string[];
  colours: { name: string; hex: string | null }[];
  priceBands: PriceBand[];
  /** Offered on /shop only (scoped pages already fix their category or collection). */
  categories: { label: string; slug: string }[];
  collections: { label: string; slug: string }[];
}

export const NO_FILTER_OPTIONS: FilterOptions = {
  sizes: [],
  colours: [],
  priceBands: [],
  categories: [],
  collections: [],
};

export function buildFilterOptions(
  facets: ApiResult<Facets>,
  extra: { categories?: ApiResult<Category[]>; collections?: ApiResult<CollectionSummary[]> } = {},
): FilterOptions {
  const data = facets.ok ? facets.data : null;
  return {
    sizes: data?.sizes ?? [],
    colours: data?.colours ?? [],
    priceBands: data ? priceBands(data.min_price, data.max_price, formatMoney) : [],
    categories:
      extra.categories?.ok
        ? extra.categories.data
            .filter((c) => c.parent_id === null)
            .sort((a, b) => a.display_order - b.display_order || a.name.localeCompare(b.name))
            .map((c) => ({ label: c.name, slug: c.slug }))
        : [],
    collections: extra.collections?.ok ? extra.collections.data.map((c) => ({ label: c.name, slug: c.slug })) : [],
  };
}
