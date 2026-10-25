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
  /** Second gallery image, shown on card hover. */
  secondary_image?: ProductImage | null;
  /** Primary (or first active) category. */
  category?: CategoryRef | null;
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
  /** Tracked stock at or below the product's low-stock threshold. */
  low_stock?: boolean;
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
  /** Published collections containing this product. */
  collections?: CategoryRef[];
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

/** Filter options available within a listing scope (GET /products/facets). */
export interface Facets {
  sizes: string[];
  colours: { name: string; hex: string | null }[];
  min_price: Money | null;
  max_price: Money | null;
  total: number;
}

export interface CollectionSummary {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image: ProductImage | null;
  seo_title: string | null;
  seo_description: string | null;
}

export interface Review {
  rating: number;
  title: string | null;
  body: string | null;
  author: string | null;
  created_at: string;
}

export interface ReviewSummary {
  average: Money | null;
  count: number;
  items: Review[];
}

export interface ShippingRule {
  name: string;
  fee: Money;
  min_order_amount: Money;
  max_order_amount: Money | null;
}

export interface SitemapEntry {
  slug: string;
  updated_at: string | null;
}

export interface Sitemap {
  products: SitemapEntry[];
  categories: SitemapEntry[];
  collections: SitemapEntry[];
  pages: SitemapEntry[];
}

// --- Cart & WhatsApp (backend-calculated; the browser only sends ids and quantities) ----------

export interface CartLine {
  item_id: string;
  product_id: string;
  variant_id: string;
  product_name: string;
  product_slug: string | null;
  sku: string | null;
  size: string | null;
  colour: string | null;
  image: ProductImage | null;
  /** Current price; null when the item can no longer be ordered. */
  price: Price | null;
  quantity: number;
  line_total: Money | null;
  available: boolean;
  max_quantity: number;
  issue: string | null;
  /** Selling price when the item was added, present only if it has changed since. */
  previous_price: Money | null;
}

export interface Cart {
  id: string | null;
  currency_code: string;
  lines: CartLine[];
  item_count: number;
  subtotal: Money;
  savings: Money;
  /** null: no delivery rule matches, so the fee is confirmed later. */
  shipping_total: Money | null;
  grand_total: Money;
  has_issues: boolean;
  has_price_changes: boolean;
}

export interface WhatsAppLink {
  reference: string;
  url: string;
  message: string;
  estimated_subtotal: Money;
  currency_code: string;
}

export interface CustomerProfile {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  roles: string[];
  is_staff: boolean;
  created_at: string | null;
}

/** Discriminated result so pages can render error/empty states instead of crashing. */
export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; message: string };
