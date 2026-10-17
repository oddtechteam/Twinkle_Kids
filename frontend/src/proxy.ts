import { type NextRequest, NextResponse } from "next/server";

/**
 * Fast pre-check for the admin area: without a session cookie there is no point rendering an
 * admin page, so redirect to sign-in. This is NOT authorization — every admin API call is
 * authenticated and permission-checked by FastAPI.
 */
const SESSION_COOKIE = "tk_session";

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (pathname === "/admin/login") return NextResponse.next();
  if (!request.cookies.has(SESSION_COOKIE)) {
    const login = new URL("/admin/login", request.url);
    login.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
