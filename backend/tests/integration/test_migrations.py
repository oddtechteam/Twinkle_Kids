"""Alembic migrations apply cleanly, seed reference data and match the ORM models.

Runs against a throwaway SQLite file; the URL is passed explicitly so the Neon URL in
.env.local is never touched. (The live suite repeats the drift check on Neon Postgres.)
"""

from pathlib import Path

from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.infrastructure.db.models import Base
from tests.conftest import alembic_config


def test_upgrade_check_and_downgrade(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    cfg = alembic_config(url)

    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if models and migrations disagree

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert set(Base.metadata.tables) <= tables
        with engine.connect() as conn:
            roles = set(conn.execute(text("select slug from roles")).scalars())
            owner_perms = conn.execute(
                text(
                    "select count(*) from role_permissions rp join roles r on r.id = rp.role_id "
                    "where r.slug = 'owner'"
                )
            ).scalar_one()
            settings_rows = conn.execute(text("select count(*) from store_settings")).scalar_one()
        assert roles == {"owner", "catalog_manager", "order_manager", "customer"}
        assert owner_perms == 10
        assert settings_rows == 1

        command.downgrade(cfg, "0002")
        assert set(inspect(engine).get_table_names()) == {"alembic_version", "media_assets"}
        command.downgrade(cfg, "base")
        assert "media_assets" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
