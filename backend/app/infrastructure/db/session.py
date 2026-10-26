import time
from typing import Any

from sqlalchemy import Engine, create_engine, event, exc

from app.infrastructure.db.url import is_pooled_neon_url, normalize_database_url

# A pooled connection used within this many seconds is trusted without a liveness ping.
IDLE_PING_AFTER_SECONDS = 30.0


def build_engine(database_url: str, *, echo: bool = False) -> Engine:
    url = normalize_database_url(database_url)
    kwargs: dict[str, Any] = {"echo": echo, "future": True}

    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Opening a connection to a distant region costs seconds (TLS + auth, plus a Neon
        # compute wake-up), so keep connections longer and reuse the most recent one (LIFO)
        # instead of churning through the pool. Liveness is checked by _ping_if_idle below.
        kwargs.update(pool_recycle=1800, pool_use_lifo=True, pool_size=5, max_overflow=5)
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

    else:
        # Like pool_pre_ping, but only for connections that sat idle: Neon's auto-suspend can
        # close those, while a connection used moments ago is alive. Each ping is a full
        # network round trip, which is expensive against a far-away database.

        @event.listens_for(engine, "checkin")
        def _mark_idle(_dbapi_conn: Any, record: Any) -> None:
            record.info["idle_since"] = time.monotonic()

        @event.listens_for(engine, "checkout")
        def _ping_if_idle(dbapi_conn: Any, record: Any, _proxy: Any) -> None:
            idle_since = record.info.get("idle_since")
            if idle_since is None or time.monotonic() - idle_since < IDLE_PING_AFTER_SECONDS:
                return
            try:
                alive = engine.dialect.do_ping(dbapi_conn)
            except Exception as error:  # any failure means a dead socket
                raise exc.DisconnectionError() from error  # the pool retries with a new one
            if not alive:
                raise exc.DisconnectionError()

    return engine
