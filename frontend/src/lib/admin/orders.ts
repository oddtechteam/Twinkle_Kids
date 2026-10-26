/**
 * Admin calls for orders and WhatsApp order requests (orders:manage permission, enforced by
 * the API). Payments are recorded manually — there is no payment gateway.
 */

import { apiFetch, apiSend } from "@/lib/api/client";
import type { Money, OrderLine, PaymentMethod, PostalAddress } from "@/lib/api/types";

export type OrderStatus =
  | "pending_confirmation"
  | "confirmed"
  | "processing"
  | "packed"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "returned";
export type PaymentStatus = "unpaid" | "paid" | "partially_refunded" | "refunded";
export type OrderSource = "website" | "whatsapp" | "admin";
export type WhatsAppStatus = "initiated" | "contacted" | "converted" | "cancelled" | "expired";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  pending_confirmation: "Pending confirmation",
  confirmed: "Confirmed",
  processing: "Processing",
  packed: "Packed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
  returned: "Returned",
};

/** Mirrors the backend workflow (the API enforces it; this only hides impossible options). */
export const ORDER_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending_confirmation: ["confirmed", "cancelled"],
  confirmed: ["processing", "cancelled"],
  processing: ["packed", "cancelled"],
  packed: ["shipped", "cancelled"],
  shipped: ["delivered", "returned"],
  delivered: ["returned"],
  cancelled: [],
  returned: [],
};

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  unpaid: "Unpaid",
  paid: "Paid (recorded)",
  partially_refunded: "Partially refunded",
  refunded: "Refunded",
};

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  cash_on_delivery: "Cash on delivery",
  upi_manual: "UPI (manual)",
  bank_transfer: "Bank transfer",
  other: "Other",
};

/** Honest labels: `initiated` only means a WhatsApp link was handed out. */
export const WHATSAPP_STATUS_LABELS: Record<WhatsAppStatus, string> = {
  initiated: "Awaiting WhatsApp confirmation",
  contacted: "Customer messaged us",
  converted: "Converted to order",
  cancelled: "Cancelled",
  expired: "Expired",
};

export type Tone = "green" | "amber" | "grey" | "red";

export function statusTone(status: OrderStatus): Tone {
  if (status === "delivered") return "green";
  if (status === "cancelled" || status === "returned") return "grey";
  return "amber";
}

export function paymentTone(status: PaymentStatus): Tone {
  return status === "paid" ? "green" : status === "unpaid" ? "amber" : "grey";
}

export function whatsappTone(status: WhatsAppStatus): Tone {
  if (status === "converted") return "green";
  if (status === "cancelled" || status === "expired") return "grey";
  return "amber";
}

export interface AdminOrderSummary {
  id: string;
  order_number: string;
  source: OrderSource;
  status: OrderStatus;
  payment_status: PaymentStatus;
  payment_method: PaymentMethod | null;
  customer_name: string;
  grand_total: Money;
  item_count: number;
  placed_at: string;
}

export interface AdminOrder {
  id: string;
  order_number: string;
  user_id: string | null;
  source: OrderSource;
  status: OrderStatus;
  payment_status: PaymentStatus;
  payment_method: PaymentMethod | null;
  placed_at: string;
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
  internal_note: string | null;
  lines: OrderLine[];
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

export interface WhatsAppRequestSummary {
  id: string;
  reference: string;
  status: WhatsAppStatus;
  customer_name: string | null;
  estimated_subtotal: Money;
  item_count: number;
  created_at: string;
  converted_order_number: string | null;
}

export interface WhatsAppRequest {
  id: string;
  reference: string;
  status: WhatsAppStatus;
  user_id: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  message_text: string;
  estimated_subtotal: Money;
  staff_note: string | null;
  contacted_at: string | null;
  created_at: string;
  converted_order_id: string | null;
  converted_order_number: string | null;
  lines: {
    variant_id: string | null;
    product_name: string;
    sku: string;
    size: string | null;
    colour: string | null;
    unit_selling_price: Money;
    quantity: number;
    line_total: Money;
  }[];
}

export interface ConvertBody {
  customer_name: string;
  customer_phone: string;
  customer_email?: string | null;
  address: PostalAddress;
  payment_method: PaymentMethod;
  items?: { variant_id: string; quantity: number }[] | null;
  internal_note?: string | null;
  apply_shipping?: boolean;
}

const query = (params: Record<string, string | number | null | undefined>) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
};

export const ordersApi = {
  list: (params: { page?: number; status?: string; source?: string; payment_status?: string; q?: string }) =>
    apiFetch<Paged<AdminOrderSummary>>(`/admin/orders${query(params)}`),
  get: (id: string) => apiFetch<AdminOrder>(`/admin/orders/${id}`),
  setStatus: (id: string, status: OrderStatus) => apiSend<AdminOrder>("PATCH", `/admin/orders/${id}/status`, { status }),
  recordPayment: (id: string, payment_status: PaymentStatus, payment_method: PaymentMethod | null) =>
    apiSend<AdminOrder>("PATCH", `/admin/orders/${id}/payment`, { payment_status, payment_method }),
  setNote: (id: string, internal_note: string | null) => apiSend<AdminOrder>("PATCH", `/admin/orders/${id}/note`, { internal_note }),

  whatsappList: (params: { page?: number; status?: string; q?: string }) =>
    apiFetch<Paged<WhatsAppRequestSummary>>(`/admin/whatsapp-requests${query(params)}`),
  whatsapp: (id: string) => apiFetch<WhatsAppRequest>(`/admin/whatsapp-requests/${id}`),
  setWhatsAppStatus: (id: string, status: WhatsAppStatus, staff_note: string | null) =>
    apiSend<WhatsAppRequest>("PATCH", `/admin/whatsapp-requests/${id}/status`, { status, staff_note }),
  convertWhatsApp: (id: string, body: ConvertBody) => apiSend<AdminOrder>("POST", `/admin/whatsapp-requests/${id}/convert`, body),
};
