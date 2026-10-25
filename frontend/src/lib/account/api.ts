/** Customer session calls (existing /api/v1/auth endpoints; HttpOnly session cookie). */

import { ApiError, apiFetch, apiSend } from "@/lib/api/client";
import type { CustomerProfile } from "@/lib/api/types";

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
