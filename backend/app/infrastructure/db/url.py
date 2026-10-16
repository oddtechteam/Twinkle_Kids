"""DATABASE_URL normalisation.

Neon (and most hosts) hand out URLs like ``postgresql://user:pass@host/db?sslmode=require``.
SQLAlchemy needs the driver named explicitly, so we map them to psycopg 3 while keeping
query parameters such as ``sslmode`` and ``channel_binding`` intact for libpq.
"""

from sqlalchemy.engine import URL, make_url

_POSTGRES_SCHEMES = {"postgres", "postgresql"}


def normalize_database_url(raw: str) -> URL:
    url = make_url(raw.strip())
    if url.drivername in _POSTGRES_SCHEMES:
        url = url.set(drivername="postgresql+psycopg")
    return url


def redact(url: URL) -> str:
    """Render a URL safe for logs (password hidden)."""
    return url.render_as_string(hide_password=True)


def is_pooled_neon_url(url: URL) -> bool:
    """Neon's pooled (PgBouncer) endpoints carry a ``-pooler`` suffix on the endpoint id."""
    host = url.host or ""
    return host.endswith(".neon.tech") and "-pooler." in host
