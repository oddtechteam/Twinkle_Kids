/**
 * Minimal typed client for the Twinkle Kids FastAPI backend (/api/v1).
 *
 * - Server code calls the API directly at API_BASE_URL (never exposed to the browser).
 * - Browser code calls the *same origin* (`/api/v1/...`), which next.config.ts rewrites to the
 *   API. Session and CSRF cookies therefore belong to the storefront origin; unsafe requests
 *   echo the readable `tk_csrf` cookie in `X-CSRF-Token` (double-submit, checked by FastAPI).
 */

const DEFAULT_BASE_URL = "http://localhost:8000";
const API_PREFIX = "/api/v1";
const CSRF_COOKIE = "tk_csrf";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);
/** Request time limit. Development defaults higher: a far-away dev database (or one waking
 *  from auto-suspend) can make a cold request legitimately slow. Override with
 *  NEXT_PUBLIC_API_TIMEOUT_MS. */
const DEFAULT_TIMEOUT_MS =
  Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS) || (process.env.NODE_ENV === "production" ? 15000 : 45000);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function apiBaseUrl(): string {
  if (typeof window !== "undefined") return ""; // same-origin, proxied by Next rewrites
  return (process.env.API_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
}

export function apiUrl(path: string): string {
  const normalised = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl()}${API_PREFIX}${normalised}`;
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

export interface ApiRequestOptions extends RequestInit {
  /** Status codes that should resolve with a parsed body instead of throwing. */
  acceptStatuses?: readonly number[];
  timeoutMs?: number;
}

export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { acceptStatuses = [], timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...init } = options;
  const method = (init.method ?? "GET").toUpperCase();
  const csrf = UNSAFE.has(method) ? readCookie(CSRF_COOKIE) : null;

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      credentials: "same-origin",
      ...init,
      headers: {
        Accept: "application/json",
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        ...headers,
      },
      signal: init.signal ?? AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    // AbortSignal.timeout rejects with a bare "signal timed out" DOMException.
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError("The store took too long to respond. Please try again.", 504, null);
    }
    throw error;
  }

  if (response.status === 204) return undefined as T;
  const body: unknown = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok && !acceptStatuses.includes(response.status)) {
    throw new ApiError(errorMessage(body, response.status), response.status, body);
  }
  return body as T;
}

/** Human-readable message from FastAPI error bodies ({detail: string | validation list}). */
export function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { loc?: unknown[]; msg?: string };
      const field = (first.loc ?? []).filter((p) => p !== "body").join(" › ");
      return field ? `${field}: ${first.msg ?? "Invalid value"}` : (first.msg ?? "Invalid request");
    }
  }
  if (status === 401) return "Please sign in again.";
  if (status === 403) return "You don't have permission to do that.";
  return `Request failed (${status}).`;
}

/** JSON helpers for mutations. */
export function apiSend<T>(method: "POST" | "PUT" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
