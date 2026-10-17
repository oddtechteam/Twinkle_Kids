/** Admin API contracts (mirrors backend/app/api/schemas/{admin,catalog,content,media}.py). */

import type { Money, Price, ProductImage } from "@/lib/api/types";

export interface AdminMe {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_staff: boolean;
  permissions: string[];
}

export type ProductStatus = "draft" | "active" | "archived";
export type PublishStatus = "draft" | "published";

export interface AdminProductSummary {
  id: string;
  name: string;
  slug: string;
  price: Price;
  from_price: Money;
  price_varies: boolean;
  in_stock: boolean;
  primary_image: ProductImage | null;
  badges: string[];
  status: ProductStatus;
  published_at: string | null;
}

export interface AdminProductList {
  items: AdminProductSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AdminVariant {
  id: string;
  sku: string;
  size: string | null;
  colour: string | null;
  colour_hex: string | null;
  price: Price;
  in_stock: boolean;
  is_active: boolean;
  selling_price_override: Money | null;
  original_price_override: Money | null;
  stock_quantity: number | null;
}

export interface AdminProductDetail {
  id: string;
  name: string;
  slug: string;
  sku: string;
  short_description: string | null;
  description: string | null;
  price: Price;
  status: ProductStatus;
  track_inventory: boolean;
  allow_backorder: boolean;
  low_stock_threshold: number;
  primary_category_id: string | null;
  size_chart_id: string | null;
  collection_ids: string[];
  badges: string[];
  variants: AdminVariant[];
  images: ProductImage[];
  categories: { id: string; name: string; slug: string }[];
  seo_title: string | null;
  seo_description: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductPayload {
  name: string;
  slug: string | null;
  sku: string;
  selling_price: string;
  original_price: string | null;
  status: ProductStatus;
  short_description: string | null;
  description: string | null;
  track_inventory: boolean;
  allow_backorder: boolean;
  low_stock_threshold: number;
  size_chart_id: string | null;
  seo_title: string | null;
  seo_description: string | null;
  category_ids: string[];
  primary_category_id: string | null;
  collection_ids: string[];
  badges: string[];
  variants: {
    id: string | null;
    sku: string;
    size: string | null;
    colour: string | null;
    colour_hex: string | null;
    selling_price: string | null;
    original_price: string | null;
    stock_quantity: number;
    is_active: boolean;
  }[];
  media: { media_asset_id: string; alt_text: string | null; variant_sku: string | null }[];
}

export interface AdminCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  parent_id: string | null;
  image: ProductImage | null;
  display_order: number;
  is_active: boolean;
  custom_product_ordering: boolean;
  seo_title: string | null;
  seo_description: string | null;
}

export interface AdminCategoryDetail {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  parent_id: string | null;
  image_media_id: string | null;
  is_active: boolean;
  display_order: number;
  custom_product_ordering: boolean;
  seo_title: string | null;
  seo_description: string | null;
  products: AdminProductSummary[];
}

export interface AdminCollection {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_media_id: string | null;
  status: PublishStatus;
  display_order: number;
  seo_title: string | null;
  seo_description: string | null;
  product_count: number | null;
}

export type SectionType =
  | "hero_banner"
  | "category_grid"
  | "product_carousel"
  | "product_grid"
  | "editorial_banner"
  | "promo_banner"
  | "collection_showcase"
  | "occasion_collection"
  | "trust_strip"
  | "testimonials"
  | "faq"
  | "announcement"
  | "contact"
  | "rich_text";

export type SelectionMode = "none" | "manual" | "category" | "collection" | "newest";

export interface Section {
  id: string;
  section_type: SectionType;
  title: string | null;
  subtitle: string | null;
  settings: Record<string, unknown>;
  is_visible: boolean;
  status: PublishStatus;
  position: number;
  desktop_media_id: string | null;
  mobile_media_id: string | null;
  selection_mode: SelectionMode;
  source_category_id: string | null;
  source_collection_id: string | null;
  product_limit: number;
  product_ids: string[];
}

export interface SectionPayload {
  section_type: SectionType;
  title: string | null;
  subtitle: string | null;
  settings: Record<string, unknown>;
  is_visible: boolean;
  desktop_media_id: string | null;
  mobile_media_id: string | null;
  selection_mode: SelectionMode;
  source_category_id: string | null;
  source_collection_id: string | null;
  product_limit: number;
}

export interface Publication {
  published_at: string | null;
  draft_modified_at: string | null;
  has_unpublished_changes: boolean;
}

export interface HomepageAdmin {
  sections: Section[];
  publication: Publication;
}

export interface MediaAsset {
  id: string;
  purpose: string;
  visibility: "public" | "private";
  url: string;
  content_type: string;
  size_bytes: number;
  width: number;
  height: number;
  alt_text: string | null;
  created_at: string;
  bucket: string;
  object_key: string;
  original_filename: string | null;
}

export interface PaymentOption {
  method: "cash_on_delivery" | "upi_manual" | "bank_transfer" | "other";
  enabled: boolean;
  label: string;
  instructions: string;
}

export interface StoreSettings {
  store_name: string;
  tagline: string | null;
  currency_code: string;
  logo_media_id: string | null;
  favicon_media_id: string | null;
  theme: Record<string, string>;
  announcement: { enabled?: boolean; message?: string; link_label?: string; link_href?: string | null };
  contact_email: string | null;
  contact_phone: string | null;
  business_address: string | null;
  business_hours: string | null;
  social_links: Record<string, string | null>;
  guest_checkout_enabled: boolean;
  whatsapp_ordering_enabled: boolean;
  whatsapp_number: string | null;
  whatsapp_message_template: string | null;
  payment_options: PaymentOption[];
  default_product_sort: string;
  default_low_stock_threshold: number;
  seo_defaults: { title_suffix?: string; default_description?: string; og_image_media_id?: string | null };
  updated_at: string | null;
}

export type NavigationMenu = "header" | "footer" | "mobile";
export type LinkType = "category" | "collection" | "page" | "url" | "heading";

export interface NavigationItem {
  id: string;
  menu: NavigationMenu;
  label: string;
  link_type: LinkType;
  parent_id: string | null;
  category_id: string | null;
  collection_id: string | null;
  page_id: string | null;
  url: string | null;
  position: number;
  is_active: boolean;
  open_in_new_tab: boolean;
}

export type PageBlock =
  | { type: "heading"; text: string; level: 2 | 3 }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "faq"; items: { question: string; answer: string }[] }
  | { type: "callout"; text: string };

export interface WebsitePage {
  id: string;
  slug: string;
  title: string;
  content: { blocks?: PageBlock[] };
  status: PublishStatus;
  seo_title: string | null;
  seo_description: string | null;
  published_at: string | null;
  updated_at: string | null;
}

export interface ShippingRule {
  id: string;
  name: string;
  fee: Money;
  min_order_amount: Money;
  max_order_amount: Money | null;
  priority: number;
  is_active: boolean;
}

export interface SizeChart {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  chart: { unit?: "cm" | "in"; columns?: string[]; rows?: string[][] };
}

export interface Dashboard {
  products_total: number;
  products_active: number;
  products_draft: number;
  products_archived: number;
  low_stock_count: number;
  out_of_stock_count: number;
  low_stock: {
    product_id: string;
    product_name: string;
    variant_label: string | null;
    sku: string;
    stock_quantity: number;
    threshold: number;
  }[];
  orders_total: number;
  orders_new: number;
  orders_by_day: { day: string; orders: number }[];
  order_value_placed: Money;
  order_value_confirmed: Money;
  revenue_paid: Money;
  whatsapp_initiated: number;
  whatsapp_contacted: number;
  top_products: { product_name: string; units: number }[];
  top_products_min_orders: number;
  recent_activity: {
    action: string;
    entity_type: string;
    entity_id: string | null;
    actor_email: string | null;
    created_at: string;
  }[];
}
