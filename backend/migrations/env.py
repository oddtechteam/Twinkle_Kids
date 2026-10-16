from logging.config import fileConfig
from typing import Any

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import Connection

from app.core.config import get_settings
from app.infrastructure.db.models import Base
from app.infrastructure.db.session import build_engine
from app.infrastructure.db.types import UTCDateTime
from app.infrastructure.db.url import normalize_database_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Migrations use the direct (non-pooled) endpoint: DDL and advisory locks need a real session.
# An explicit sqlalchemy.url (set programmatically, e.g. by tests) takes precedence.
explicit_url = config.get_main_option("sqlalchemy.url")
settings = get_settings()
database_url = explicit_url or settings.migration_database_url


def _guard_production() -> None:
    """Never change a production database just because a connection string is available."""
    try:  # upgrade/downgrade/stamp have a destination; revision/current/check do not
        mutating = context.get_revision_argument() is not None
    except KeyError:
        mutating = False
    if explicit_url or not mutating or not settings.targets_production_data:
        return
    if context.get_x_argument(as_dictionary=True).get("confirm_production") == "yes":
        return
    raise SystemExit(
        "Refusing to migrate production data "
        f"(APP_ENV={settings.app_env}, NEON_BRANCH={settings.neon_branch}).\n"
        "Review the migration (alembic upgrade head --sql), take a backup/branch snapshot, then "
        "re-run with:  alembic -x confirm_production=yes upgrade head"
    )


def _render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | bool:
    # Keep migrations independent of application code: UTCDateTime is a plain timestamptz.
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def _configure(**kwargs: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        render_item=_render_item,
        render_as_batch=normalize_database_url(database_url).get_backend_name() == "sqlite",
        **kwargs,  # type: ignore[arg-type]
    )


def run_migrations_offline() -> None:
    _configure(
        url=normalize_database_url(database_url).render_as_string(hide_password=False),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    _guard_production()
    engine = build_engine(database_url)
    with engine.connect() as connection:
        _run_with(connection)
    engine.dispose()


def _run_with(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
