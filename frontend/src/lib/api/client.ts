/**
 * Minimal typed client for the Twinkle Kids FastAPI backend (/api/v1).
 * Server components use API_BASE_URL (internal); browser code uses NEXT_PUBLIC_API_BASE_URL.
 */

const DEFAULT_BASE_URL = "http://localhost:8000";
const API_PREFIX = "/api/v1";

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
  const fromEnv =
    typeof window === "undefined"
      ? (process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL)
      : process.env.NEXT_PUBLIC_API_BASE_URL;
  return (fromEnv ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
}

export function apiUrl(path: string): string {
  const normalised = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl()}${API_PREFIX}${normalised}`;
}

export interface ApiRequestOptions extends RequestInit {
  /** Status codes that should resolve with a parsed body instead of throwing. */
  acceptStatuses?: readonly number[];
  timeoutMs?: number;
}

export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { acceptStatuses = [], timeoutMs = 8000, headers, ...init } = options;

  const response = await fetch(apiUrl(path), {
    ...init,
    headers: { Accept: "application/json", ...headers },
    signal: init.signal ?? AbortSignal.timeout(timeoutMs),
  });

  const body: unknown = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok && !acceptStatuses.includes(response.status)) {
    throw new ApiError(`API ${response.status} for ${path}`, response.status, body);
  }
  return body as T;
}
