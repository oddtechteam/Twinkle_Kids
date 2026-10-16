from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select

from app import cli
from app.core.config import Settings
from app.infrastructure.db.models.catalog import ProductModel, ProductVariantModel
from app.infrastructure.db.models.commerce import InventoryMovementModel
from app.infrastructure.db.models.identity import UserModel
from tests.conftest import make_settings

ADMIN_PASSWORD = "twinkle stars over the bay 2026"  # test-only credential


@pytest.fixture
def cli_settings(db_path: Path) -> Settings:
    return make_settings(db_path)


def run(settings: Settings, *argv: str) -> int:
    return cli.main(list(argv), settings=settings)


def test_create_admin_from_env_var(
    cli_settings: Settings, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TK_ADMIN_PASSWORD", ADMIN_PASSWORD)
    code = run(
        cli_settings,
        "create-admin",
        "--email",
        "Owner@TwinkleKids.in",
        "--password-env",
        "TK_ADMIN_PASSWORD",
    )
    output = capsys.readouterr()
    assert code == 0
    assert "owner@twinklekids.in" in output.out and "owner" in output.out
    assert ADMIN_PASSWORD not in output.out + output.err  # never printed

    engine = create_engine(cli_settings.database_url)
    with engine.connect() as conn:
        user = conn.execute(select(UserModel.password_hash)).scalar_one()
    engine.dispose()
    assert user.startswith("$argon2id$")

    # Running again without --promote refuses to touch the existing account.
    assert (
        run(
            cli_settings,
            "create-admin",
            "--email",
            "owner@twinklekids.in",
            "--password-env",
            "TK_ADMIN_PASSWORD",
        )
        == 1
    )


def test_create_admin_enforces_strong_password(
    cli_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TK_ADMIN_PASSWORD", "too-short")
    assert (
        run(
            cli_settings,
            "create-admin",
            "--email",
            "o@twinklekids.in",
            "--password-env",
            "TK_ADMIN_PASSWORD",
        )
        == 1
    )
    monkeypatch.delenv("TK_ADMIN_PASSWORD")
    with pytest.raises(SystemExit):
        run(
            cli_settings,
            "create-admin",
            "--email",
            "o@twinklekids.in",
            "--password-env",
            "TK_ADMIN_PASSWORD",
        )


@pytest.mark.parametrize(
    "overrides",
    [{"neon_branch": "production"}, {"neon_branch": "main"}],
)
def test_seed_refuses_production_data(db_path: Path, overrides: dict[str, object]) -> None:
    assert run(make_settings(db_path, **overrides), "seed-demo") == 2


def test_seed_refuses_staging_without_opt_in(db_path: Path) -> None:
    staging = make_settings(db_path, app_env="staging")
    assert run(staging, "seed-demo") == 2


def test_seed_is_repeatable(cli_settings: Settings, capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli_settings, "seed-demo") == 0
    assert run(cli_settings, "seed-demo") == 0
    out = capsys.readouterr().out
    assert "10 created, 0 refreshed" in out and "0 created, 10 refreshed" in out

    engine = create_engine(cli_settings.database_url)
    with engine.connect() as conn:
        names = conn.execute(select(ProductModel.name)).scalars().all()
        variants = conn.execute(select(func.count()).select_from(ProductVariantModel)).scalar_one()
        movements = conn.execute(
            select(func.count()).select_from(InventoryMovementModel)
        ).scalar_one()
    engine.dispose()
    assert len(names) == 6 and all(n.startswith("[Demo] ") for n in names)
    assert variants == 28
    assert movements == 22  # initial stock recorded once; re-seeding changes nothing
