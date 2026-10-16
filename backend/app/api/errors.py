"""Maps domain/infrastructure errors to HTTP responses without leaking internals."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    MediaTooLargeError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    StorageUnavailableError,
    UnsupportedMediaTypeError,
)

logger = logging.getLogger(__name__)

# Most specific first: the first isinstance match wins.
_STATUS_BY_ERROR: list[tuple[type[Exception], int]] = [
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (MediaTooLargeError, status.HTTP_413_CONTENT_TOO_LARGE),
    (UnsupportedMediaTypeError, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    (DomainValidationError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (PermissionDeniedError, status.HTTP_403_FORBIDDEN),
]


def register_error_handlers(app: FastAPI) -> None:
    async def domain_error(_: Request, exc: Exception) -> JSONResponse:
        for error_type, code in _STATUS_BY_ERROR:
            if isinstance(exc, error_type):
                return JSONResponse({"detail": str(exc)}, status_code=code)
        raise exc  # pragma: no cover

    async def rate_limited(_: Request, exc: Exception) -> JSONResponse:
        retry_after = getattr(exc, "retry_after_seconds", 60)
        return JSONResponse(
            {"detail": str(exc)},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
        )

    async def storage_error(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Storage unavailable: %s", exc.__cause__.__class__.__name__)
        return JSONResponse(
            {"detail": "File storage is temporarily unavailable."},
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    for error_type, _code in _STATUS_BY_ERROR:
        app.add_exception_handler(error_type, domain_error)
    app.add_exception_handler(RateLimitedError, rate_limited)
    app.add_exception_handler(StorageUnavailableError, storage_error)
