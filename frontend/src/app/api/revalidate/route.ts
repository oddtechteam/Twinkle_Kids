import { revalidateTag } from "next/cache";
import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { SITE_CONTENT_TAG } from "@/lib/content";

/**
 * Expires the cached storefront content right after an admin publishes changes.
 *
 * Protection: same-origin request, double-submit CSRF token, and the caller's session must
 * belong to staff with content or settings permissions — verified by FastAPI (/admin/me).
 * Only the fixed `site-content` tag can be revalidated; callers cannot pick arbitrary tags.
 */
const API_ORIGIN = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const ALLOWED_PERMISSIONS = ["content:manage", "settings:manage", "catalog:manage"];

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (origin && origin !== request.nextUrl.origin) {
    return NextResponse.json({ detail: "Cross-site request blocked." }, { status: 403 });
  }

  const jar = await cookies();
  const session = jar.get("tk_session")?.value;
  const csrf = jar.get("tk_csrf")?.value;
  if (!session || !csrf || request.headers.get("x-csrf-token") !== csrf) {
    return NextResponse.json({ detail: "Not authorised." }, { status: 403 });
  }

  const me = await fetch(`${API_ORIGIN}/api/v1/admin/me`, {
    headers: { Cookie: `tk_session=${session}`, Accept: "application/json" },
    cache: "no-store",
  }).catch(() => null);
  if (!me || !me.ok) {
    return NextResponse.json({ detail: "Not authorised." }, { status: 403 });
  }
  const profile = (await me.json()) as { permissions?: string[] };
  if (!profile.permissions?.some((p) => ALLOWED_PERMISSIONS.includes(p))) {
    return NextResponse.json({ detail: "Not authorised." }, { status: 403 });
  }

  revalidateTag(SITE_CONTENT_TAG, { expire: 0 });
  return NextResponse.json({ revalidated: true });
}
