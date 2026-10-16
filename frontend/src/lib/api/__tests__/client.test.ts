import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch, apiUrl } from "../client";
import { getReadiness } from "../health";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("apiUrl", () => {
  it("prefixes the versioned API path and trims trailing slashes", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/");
    expect(apiUrl("health")).toBe("https://api.example.com/api/v1/health");
    expect(apiUrl("/health/ready")).toBe("https://api.example.com/api/v1/health/ready");
  });
});

describe("apiFetch", () => {
  it("returns parsed JSON for successful responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ ok: true })));
    await expect(apiFetch("/x")).resolves.toEqual({ ok: true });
  });

  it("throws ApiError with status and body on failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "nope" }, 404)));
    const error = await apiFetch("/x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, body: { detail: "nope" } });
  });
});

describe("getReadiness", () => {
  it("treats a 503 as a reachable API with a degraded report", async () => {
    const report = { status: "down", components: [{ name: "database", state: "down" }] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(report, 503)));
    await expect(getReadiness()).resolves.toEqual({ reachable: true, report });
  });

  it("reports unreachable when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    await expect(getReadiness()).resolves.toEqual({ reachable: false, error: "fetch failed" });
  });
});
