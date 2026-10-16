"""Browser-session cookies and cross-site request protection.

* Session cookie: random opaque token, HttpOnly, SameSite (default Lax), Secure outside dev.
* CSRF: double-submit token. A readable ``tk_csrf`` cookie is issued with the session; any
  state-changing request that carries the session cookie must echo it in ``X-CSRF-Token``.
* Origin check: state-changing requests with an ``Origin`` header must come from a trusted
  origin (CORS_ORIGINS) — this also covers login/register, which have no session yet.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from app.application.use_cases.auth import IssuedSession
from app.core.config import Settings
from app.core.security import new_token, tokens_match

CSRF_HEADER = "x-csrf-token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def set_session_cookies(response: Response, settings: Settings, issued: IssuedSession) -> None:
    max_age = int((issued.session.expires_at - issued.session.created_at).total_seconds())
    common = {
        "max_age": max_age,
        "secure": settings.secure_cookies,
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.set_cookie(settings.session_cookie_name, issued.token, httponly=True, **common)  # type: ignore[arg-type]
    response.set_cookie(settings.csrf_cookie_name, new_token(), httponly=False, **common)  # type: ignore[arg-type]


def clear_session_cookies(response: Response, settings: Settings) -> None:
    for name, http_only in (
        (settings.session_cookie_name, True),
        (settings.csrf_cookie_name, False),
    ):
        response.delete_cookie(
            name,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.secure_cookies,
            httponly=http_only,
            samesite=settings.cookie_samesite,
        )


def csrf_protection(
    settings: Settings, *, exempt_paths: frozenset[str]
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    trusted = frozenset(origin.rstrip("/") for origin in settings.cors_origins)

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in UNSAFE_METHODS:
            origin = request.headers.get("origin")
            own_origin = f"{request.url.scheme}://{request.url.netloc}"
            if origin and origin.rstrip("/") not in trusted and origin != own_origin:
                return JSONResponse(
                    {"detail": "Cross-site request blocked."}, status.HTTP_403_FORBIDDEN
                )
            has_session = settings.session_cookie_name in request.cookies
            if has_session and request.url.path not in exempt_paths:
                cookie = request.cookies.get(settings.csrf_cookie_name)
                header = request.headers.get(CSRF_HEADER)
                if not cookie or not header or not tokens_match(cookie, header):
                    return JSONResponse(
                        {"detail": "Missing or invalid CSRF token."}, status.HTTP_403_FORBIDDEN
                    )
        return await call_next(request)

    return middleware
