/**
 * Browser calls for the server-side bag (`/api/v1/cart`, proxied same-origin).
 * Only variant ids and quantities are ever sent; every price and total comes back from the API.
 */

import { ApiError, apiFetch, apiSend } from "@/lib/api/client";
import type { Cart, WhatsAppLink } from "@/lib/api/types";

export function fetchCart(): Promise<Cart> {
  return apiFetch<Cart>("/cart", { cache: "no-store" });
}

export function addCartItem(variantId: string, quantity: number): Promise<Cart> {
  return apiSend<Cart>("POST", "/cart/items", { variant_id: variantId, quantity });
}

export function updateCartItem(itemId: string, quantity: number): Promise<Cart> {
  return apiSend<Cart>("PATCH", `/cart/items/${encodeURIComponent(itemId)}`, { quantity });
}

export function removeCartItem(itemId: string): Promise<Cart> {
  return apiSend<Cart>("DELETE", `/cart/items/${encodeURIComponent(itemId)}`);
}

export function acknowledgeCartPrices(): Promise<Cart> {
  return apiSend<Cart>("POST", "/cart/acknowledge-prices");
}

/**
 * Records a WhatsApp order *request* and returns the click-to-chat link. Opening the link is
 * not proof that a message was sent; staff confirm requests in the admin panel.
 */
export function startWhatsAppRequest(items: { variantId: string; quantity: number }[]): Promise<WhatsAppLink> {
  return apiSend<WhatsAppLink>("POST", "/whatsapp-requests", {
    items: items.map((item) => ({ variant_id: item.variantId, quantity: item.quantity })),
  });
}

/** Customer-facing message from an API failure (the backend writes these for shoppers). */
export function bagErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status >= 500) return "Something went wrong on our side. Please try again.";
    return error.message;
  }
  return "We couldn't reach the store. Check your connection and try again.";
}
