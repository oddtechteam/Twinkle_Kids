/**
 * Types mirroring the FastAPI catalogue contracts (backend/app/api/schemas/catalog.py).
 * Money is a decimal *string* (e.g. "399.00") exactly as the API serialises it — it is only
 * formatted for display, never used to calculate authoritative totals in the browser.
 */

export type Money = string;

export interface Price {
  selling_price: Money;
  original_price: Money | null;
  /** Present only when original_price is a valid, higher comparison price. */
  discount_amount: Money | null;
  discount_percent: number | null;
  currency: string;
}

export interface ProductImage {
  media_asset_id: string;
  url: string;
  alt_text: string | null;
  width: number;
  height: number;
  variant_id?: string | null;
}

export interface CategoryRef {
  id: string;
  name: string;
  slug: string;
}

export interface ProductSummary {
  id: string;
  name: string;
  slug: string;
  price: Price;
  /** Lowest effective selling price across active variants. */
  from_price: Money;
  price_varies: boolean;
  in_stock: boolean;
  primary_image: ProductImage | null;
  /** Admin-managed labels such as "New season". */
  badges?: string[];
}

export interface ProductList {
  items: ProductSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ProductVariant {
  id: string;
  sku: string;
  size: string | null;
  colour: string | null;
  colour_hex: string | null;
  price: Price;
  in_stock: boolean;
  is_active: boolean;
}

export interface SizeChart {
  name?: string;
  unit?: string;
  columns?: string[];
  rows?: string[][];
  [key: string]: unknown;
}

export interface ProductDetail {
  id: string;
  name: string;
  slug: string;
  sku: string;
  short_description: string | null;
  description: string | null;
  rich_content: Record<string, unknown> | null;
  price: Price;
  in_stock: boolean;
  sizes: string[];
  colours: string[];
  variants: ProductVariant[];
  images: ProductImage[];
  categories: CategoryRef[];
  size_chart: SizeChart | null;
  seo_title: string | null;
  seo_description: string | null;
  seo_metadata: Record<string, unknown>;
  published_at: string | null;
  badges?: string[];
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  parent_id: string | null;
  image: ProductImage | null;
  display_order: number;
  seo_title: string | null;
  seo_description: string | null;
}

export interface CategoryDetail {
  category: Category;
  children: Category[];
  breadcrumbs: CategoryRef[];
  seo_metadata: Record<string, unknown>;
  products: ProductList;
}

export type ProductSort = "featured" | "newest" | "price_asc" | "price_desc" | "name_asc";

/** Discriminated result so pages can render error/empty states instead of crashing. */
export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; message: string };
