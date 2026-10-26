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
  /** Admin-cropped renditions keyed by frame (see lib/media/frames.ts). */
  crops?: Partial<Record<string, { url: string; width: number; height: number }>>;
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

export type ProductSort = "featured" | "bestselling" | "newest" | "price_asc" | "price_desc" | "name_asc";

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
  /** Set by the server only when the reviewer has a real order for this product. */
  verified_purchase?: boolean;
  images?: ProductImage[];
}

export interface ReviewSummary {
  average: Money | null;
  count: number;
  items: Review[];
}

/** GET /products/{slug}/recommendations: shop-curated picks, then real same-category bestsellers. */
export interface Recommendations {
  curated: ProductSummary[];
  bestsellers: ProductSummary[];
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

// --- Checkout & orders (all money calculated by the backend) ----------------------------------

export type PaymentMethod = "cash_on_delivery" | "upi_manual" | "bank_transfer" | "other";

export interface PostalAddress {
  full_name: string;
  phone: string;
  line1: string;
  line2?: string | null;
  landmark?: string | null;
  city: string;
  state: string;
  postal_code: string;
}

export interface SavedAddress extends PostalAddress {
  id: string;
  label: string | null;
  is_default: boolean;
  country_code: string;
}

export interface PaymentOption {
  method: PaymentMethod;
  label: string;
  instructions: string;
}

export interface CheckoutQuote {
  bag: Cart;
  currency_code: string;
  subtotal: Money;
  discount_total: Money;
  shipping_total: Money;
  /** False when no delivery rule matched: the shop confirms any delivery charge. */
  shipping_configured: boolean;
  grand_total: Money;
  coupon_code: string | null;
  coupon_error: string | null;
  payment_methods: PaymentOption[];
  guest_checkout_enabled: boolean;
  signed_in: boolean;
  can_place_order: boolean;
  blocking_reason: string | null;
}

export interface OrderLine {
  product_name: string;
  product_slug: string | null;
  sku: string;
  size: string | null;
  colour: string | null;
  image_url: string | null;
  unit_selling_price: Money;
  unit_original_price: Money | null;
  quantity: number;
  line_total: Money;
}

/** A customer's view of an order: what was bought — no internal status or tracking. */
export interface CustomerOrder {
  order_number: string;
  placed_at: string;
  payment_method: PaymentMethod | null;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  shipping_address: PostalAddress & { country_code?: string };
  currency_code: string;
  subtotal: Money;
  discount_total: Money;
  shipping_total: Money;
  grand_total: Money;
  coupon_code: string | null;
  customer_note: string | null;
  lines: OrderLine[];
  payment_instructions?: string | null;
}

export interface CustomerOrderSummary {
  order_number: string;
  placed_at: string;
  grand_total: Money;
  item_count: number;
}

export interface CustomerOrderList {
  items: CustomerOrderSummary[];
  total: number;
  page: number;
  pages: number;
}
