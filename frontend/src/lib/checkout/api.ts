/** Browser calls for website checkout. Only details and choices are sent — never prices. */

import { apiFetch, apiSend } from "@/lib/api/client";
import type { CheckoutQuote, CustomerOrder, PaymentMethod, PostalAddress } from "@/lib/api/types";

export interface CheckoutSubmission {
  customer_name: string;
  customer_phone: string;
  customer_email?: string | null;
  address?: PostalAddress | null;
  saved_address_id?: string | null;
  payment_method: PaymentMethod;
  customer_note?: string | null;
  coupon_code?: string | null;
  save_address?: boolean;
  /** The total the shopper saw; the backend refuses (409) if its own total differs. */
  expected_grand_total?: string | null;
}

export function fetchQuote(couponCode: string | null): Promise<CheckoutQuote> {
  return apiSend<CheckoutQuote>("POST", "/checkout/quote", { coupon_code: couponCode || null });
}

/** The same key is reused for retries of one attempt, so a double submit returns one order. */
export function placeOrder(body: CheckoutSubmission, idempotencyKey: string): Promise<CustomerOrder> {
  return apiFetch<CustomerOrder>("/checkout/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(body),
  });
}

/** Placed orders are kept for the confirmation page in this tab only (works for guests). */
const KEY = (reference: string) => `tk-order:${reference}`;

export function rememberOrder(order: CustomerOrder): void {
  try {
    sessionStorage.setItem(KEY(order.order_number), JSON.stringify(order));
  } catch {
    // Storage blocked: signed-in customers can still load the order from their account.
  }
}

export function recalledOrder(reference: string): CustomerOrder | null {
  try {
    const raw = sessionStorage.getItem(KEY(reference));
    return raw ? (JSON.parse(raw) as CustomerOrder) : null;
  } catch {
    return null;
  }
}

/** Whether the shop delivers to a PIN code, from its own coverage rules (no courier lookup). */
export function checkPin(postalCode: string): Promise<{ serviceable: boolean; message: string | null }> {
  return apiFetch(`/checkout/pin/${encodeURIComponent(postalCode)}`, { cache: "no-store" });
}
