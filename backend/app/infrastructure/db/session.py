from typing import Any

from sqlalchemy import Engine, create_engine, event

from app.infrastructure.db.url import is_pooled_neon_url, normalize_database_url


def build_engine(database_url: str, *, echo: bool = False) -> Engine:
    url = normalize_database_url(database_url)
    kwargs: dict[str, Any] = {"echo": echo, "future": True}

    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Neon's free tier auto-suspends idle compute; pre-ping and recycle avoid stale sockets.
        kwargs.update(pool_pre_ping=True, pool_recycle=300, pool_size=5, max_overflow=5)
        if is_pooled_neon_url(url):
            # The pooled endpoint is PgBouncer in transaction mode: don't let psycopg create
            # server-side prepared statements that may land on a different backend connection.
            kwargs["connect_args"] = {"prepare_threshold": None}

    engine = create_engine(url, **kwargs)

    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fks(dbapi_conn: Any, _record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine
