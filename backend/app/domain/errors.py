"""Domain-level errors. The API layer maps these to HTTP responses."""


class DomainError(Exception):
    """Base class for expected, user-facing business errors."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    """A uniqueness or state conflict (duplicate slug, SKU, email...)."""


class DomainValidationError(DomainError):
    """Input violates a business rule."""


class PricingError(DomainValidationError):
    pass


class MediaValidationError(DomainValidationError):
    """The uploaded file is not acceptable."""


class UnsupportedMediaTypeError(MediaValidationError):
    pass


class MediaTooLargeError(MediaValidationError):
    pass


class AuthenticationError(DomainError):
    """Credentials or session are missing/invalid. Messages are deliberately generic."""


class PermissionDeniedError(DomainError):
    pass


class RateLimitedError(DomainError):
    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class StorageUnavailableError(Exception):
    """The object store failed. Infrastructure detail is logged, never shown to clients."""
