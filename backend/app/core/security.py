"""Token helpers shared by the auth use cases and the HTTP layer."""

import hashlib
import secrets

SESSION_TOKEN_BYTES = 32  # 256-bit, URL-safe


def new_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Session tokens are stored only as SHA-256 digests (high-entropy, so no salt needed)."""
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())
