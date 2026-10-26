/**
 * Admin calls for store operations. Each route checks its own permission on the server
 * (inventory:manage, settings:manage, orders:manage, content:manage, users:manage, audit:read).
 */

import { apiFetch, apiSend } from "@/lib/api/client";
import type { Money, ProductImage } from "@/lib/api/types";
import type { Paged } from "./orders";

const query = (params: Record<string, string | number | null | undefined>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
};

// --- inventory ---------------------------------------------------------------------------------

export type StockState = "in_stock" | "low_stock" | "out_of_stock" | "untracked";
export type AdjustReason = "restock" | "adjustment" | "damaged" | "return";

export const STOCK_STATE_LABELS: Record<StockState, string> = {
  in_stock: "In stock",
  low_stock: "Low stock",
  out_of_stock: "Out of stock",
  untracked: "Not tracked",
};

export const MOVEMENT_LABELS: Record<string, string> = {
  initial_stock: "Opening stock",
  restock: "Restock",
  adjustment: "Adjustment",
  order_placed: "Sold (order placed)",
  order_cancelled: "Order cancelled",
  return: "Return received",
  damaged: "Damaged / lost",
};

export interface InventoryRow {
  variant_id: string;
  product_id: string;
  product_name: string;
  product_status: string;
  sku: string;
  size: string | null;
  colour: string | null;
  stock_quantity: number;
  low_stock_threshold: number;
  track_inventory: boolean;
  allow_backorder: boolean;
  is_active: boolean;
  state: StockState;
}

export interface Movement {
  id: string;
  variant_id: string;
  sku: string;
  product_name: string;
  quantity_delta: number;
  stock_after: number;
  reason: string;
  note: string | null;
  order_number: string | null;
  actor_email: string | null;
  created_at: string;
}

// --- coupons -----------------------------------------------------------------------------------

export interface Coupon {
  id: string;
  code: string;
  description: string | null;
  discount_type: "percentage" | "fixed_amount";
  discount_value: Money;
  is_active: boolean;
  min_order_amount: Money | null;
  max_discount_amount: Money | null;
  starts_at: string | null;
  ends_at: string | null;
  usage_limit: number | null;
  per_user_limit: number | null;
  product_ids: string[];
  category_ids: string[];
  collection_ids: string[];
  times_used: number;
  discount_given: Money;
}

export type CouponBody = Omit<Coupon, "id" | "times_used" | "discount_given">;

// --- after-sale requests -----------------------------------------------------------------------

export type RequestKind = "cancellation" | "return" | "exchange";
export type RequestStatus = "requested" | "approved" | "rejected" | "received" | "completed";

export const REQUEST_STATUS_LABELS: Record<RequestStatus, string> = {
  requested: "Awaiting decision",
  approved: "Approved",
  rejected: "Rejected",
  received: "Goods received",
  completed: "Completed",
};

export interface OrderRequest {
  id: string;
  reference: string;
  order_id: string;
  order_number: string;
  kind: RequestKind;
  status: RequestStatus;
  reason: string;
  customer_message: string | null;
  items: { sku: string; quantity: number }[];
  resolution_note: string | null;
  refund_amount: Money | null;
  restocked: boolean;
  created_by_staff: boolean;
  created_at: string;
  updated_at: string;
}

// --- reviews -----------------------------------------------------------------------------------

export type ReviewStatus = "pending" | "approved" | "rejected";

export interface ModerationReview {
  id: string;
  product_id: string;
  product_name: string;
  product_slug: string;
  rating: number;
  title: string | null;
  body: string | null;
  author_name: string | null;
  author_email: string | null;
  is_verified_purchase: boolean;
  status: ReviewStatus;
  moderation_note: string | null;
  images: ProductImage[];
  created_at: string;
}

// --- analytics ---------------------------------------------------------------------------------

export interface Analytics {
  start: string;
  end: string;
  orders_placed: number;
  orders_cancelled: number;
  website_orders: number;
  whatsapp_orders: number;
  order_value_placed: Money;
  payments_recorded: Money;
  refunds_recorded: Money;
  average_order_value: Money | null;
  whatsapp_requests: number;
  whatsapp_contacted: number;
  whatsapp_converted: number;
  by_day: { day: string; website_orders: number; whatsapp_orders: number; order_value: Money }[];
  top_products: { product_id: string | null; product_name: string; units: number; order_value: Money }[];
  categories: { category: string; units: number; order_value: Money }[];
  coupons: { code: string; redemptions: number; discount_given: Money }[];
}

// --- staff, audit, notifications ----------------------------------------------------------------

export type StaffRole = "owner" | "catalog_manager" | "order_manager";

export const ROLE_LABELS: Record<StaffRole, string> = {
  owner: "Super administrator",
  catalog_manager: "Catalogue manager",
  order_manager: "Order manager",
};

export interface StaffMember {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
  last_login_at: string | null;
}

export interface AuditEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_email: string | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface NotificationEntry {
  id: string;
  channel: "email" | "whatsapp";
  template: string;
  recipient: string;
  subject: string | null;
  status: "sent" | "failed" | "skipped";
  provider: string | null;
  error: string | null;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string | null;
}

export const opsApi = {
  inventory: (params: { page?: number; q?: string; state?: string }) =>
    apiFetch<Paged<InventoryRow>>(`/admin/inventory${query(params)}`),
  adjustStock: (variantId: string, body: { delta: number; reason: AdjustReason; note: string | null }) =>
    apiSend<InventoryRow>("POST", `/admin/inventory/${variantId}/adjust`, body),
  movements: (params: { page?: number; variant_id?: string }) =>
    apiFetch<Paged<Movement>>(`/admin/inventory/movements${query(params)}`),

  coupons: () => apiFetch<Coupon[]>("/admin/coupons"),
  createCoupon: (body: CouponBody) => apiSend<Coupon>("POST", "/admin/coupons", body),
  updateCoupon: (id: string, body: CouponBody) => apiSend<Coupon>("PUT", `/admin/coupons/${id}`, body),
  setCouponActive: (id: string, is_active: boolean) => apiSend<Coupon>("PATCH", `/admin/coupons/${id}/active`, { is_active }),

  requests: (params: { page?: number; status?: string; kind?: string }) =>
    apiFetch<Paged<OrderRequest>>(`/admin/order-requests${query(params)}`),
  request: (id: string) => apiFetch<OrderRequest>(`/admin/order-requests/${id}`),
  decide: (id: string, approve: boolean, note: string | null) =>
    apiSend<OrderRequest>("POST", `/admin/order-requests/${id}/decision`, { approve, note }),
  received: (id: string, restock: boolean, note: string | null) =>
    apiSend<OrderRequest>("POST", `/admin/order-requests/${id}/received`, { restock, note }),
  complete: (id: string, refund_amount: string | null, note: string | null) =>
    apiSend<OrderRequest>("POST", `/admin/order-requests/${id}/complete`, { refund_amount, note }),

  reviews: (params: { page?: number; status?: string }) =>
    apiFetch<Paged<ModerationReview>>(`/admin/reviews${query({ status: "pending", ...params })}`),
  moderate: (id: string, status: "approved" | "rejected", note: string | null) =>
    apiSend<void>("PATCH", `/admin/reviews/${id}`, { status, note }),

  analytics: (params: { start?: string; end?: string }) => apiFetch<Analytics>(`/admin/analytics${query(params)}`),

  staff: () => apiFetch<StaffMember[]>("/admin/staff"),
  setRoles: (email: string, roles: StaffRole[]) => apiSend<StaffMember>("PUT", "/admin/staff/roles", { email, roles }),
  audit: (params: { page?: number; action?: string; entity_type?: string }) =>
    apiFetch<Paged<AuditEntry>>(`/admin/audit-log${query(params)}`),
  notifications: (params: { page?: number; status?: string }) =>
    apiFetch<Paged<NotificationEntry>>(`/admin/notifications${query(params)}`),
};
