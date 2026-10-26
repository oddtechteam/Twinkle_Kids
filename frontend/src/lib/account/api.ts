/** Customer session calls (existing /api/v1/auth endpoints; HttpOnly session cookie). */

import { ApiError, apiFetch, apiSend } from "@/lib/api/client";
import type {
  CustomerOrder,
  CustomerOrderList,
  CustomerProfile,
  PostalAddress,
  SavedAddress,
} from "@/lib/api/types";

/** The signed-in customer, or null for guests. */
export async function fetchMe(): Promise<CustomerProfile | null> {
  try {
    return await apiFetch<CustomerProfile>("/auth/me", { cache: "no-store" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export function signIn(email: string, password: string): Promise<CustomerProfile> {
  return apiSend<CustomerProfile>("POST", "/auth/login", { email, password });
}

export function register(input: {
  fullName: string;
  email: string;
  password: string;
  phone?: string;
}): Promise<CustomerProfile> {
  return apiSend<CustomerProfile>("POST", "/auth/register", {
    full_name: input.fullName,
    email: input.email,
    password: input.password,
    phone: input.phone?.trim() || null,
  });
}

export function signOut(): Promise<void> {
  return apiSend<void>("POST", "/auth/logout");
}

/** Only same-site paths are followed after sign-in (no open redirects). */
export function safeNextPath(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return null;
  return value;
}

// --- profile, password, addresses and order history ------------------------------------------

export function updateProfile(input: { fullName: string; phone: string }): Promise<CustomerProfile> {
  return apiSend<CustomerProfile>("PATCH", "/account/profile", {
    full_name: input.fullName,
    phone: input.phone.trim() || null,
  });
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return apiSend<void>("POST", "/account/password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

/** Always resolves the same way whether or not the email has an account. */
export function requestPasswordReset(email: string): Promise<{ detail: string }> {
  return apiSend<{ detail: string }>("POST", "/auth/password-reset/request", { email });
}

export function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  return apiSend<void>("POST", "/auth/password-reset/confirm", { token, new_password: newPassword });
}

export type AddressInput = PostalAddress & { label?: string | null; is_default?: boolean };

export function listAddresses(): Promise<SavedAddress[]> {
  return apiFetch<SavedAddress[]>("/account/addresses", { cache: "no-store" });
}

export function addAddress(input: AddressInput): Promise<SavedAddress> {
  return apiSend<SavedAddress>("POST", "/account/addresses", input);
}

export function updateAddress(id: string, input: AddressInput): Promise<SavedAddress> {
  return apiSend<SavedAddress>("PUT", `/account/addresses/${encodeURIComponent(id)}`, input);
}

export function deleteAddress(id: string): Promise<void> {
  return apiSend<void>("DELETE", `/account/addresses/${encodeURIComponent(id)}`);
}

export function listMyOrders(page = 1): Promise<CustomerOrderList> {
  return apiFetch<CustomerOrderList>(`/account/orders?page=${page}`, { cache: "no-store" });
}

export function fetchMyOrder(reference: string): Promise<CustomerOrder> {
  return apiFetch<CustomerOrder>(`/account/orders/${encodeURIComponent(reference)}`, { cache: "no-store" });
}

export type OrderRequestKind = "cancellation" | "return" | "exchange";

/** A request I raised on one of my orders, with the shop's decision. */
export interface MyOrderRequest {
  reference: string;
  kind: OrderRequestKind;
  status: "requested" | "approved" | "rejected" | "received" | "completed";
  reason: string;
  customer_message: string | null;
  resolution_note: string | null;
  created_at: string;
}

export function listOrderRequests(orderNumber: string): Promise<MyOrderRequest[]> {
  return apiFetch<MyOrderRequest[]>(`/account/orders/${encodeURIComponent(orderNumber)}/requests`, { cache: "no-store" });
}

export function createOrderRequest(
  orderNumber: string,
  input: { kind: OrderRequestKind; reason: string; message: string | null },
): Promise<MyOrderRequest> {
  return apiSend<MyOrderRequest>("POST", `/account/orders/${encodeURIComponent(orderNumber)}/requests`, { ...input, items: [] });
}
