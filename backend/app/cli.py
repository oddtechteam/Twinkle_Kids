"""Operational commands.

    python -m app.cli create-admin --email owner@example.com --name "Store Owner"
    python -m app.cli create-admin --email owner@example.com --password-env TK_ADMIN_PASSWORD
    python -m app.cli seed-demo            # development/test databases only

Passwords are read interactively (hidden) or from a named environment variable, validated,
and never printed or logged.
"""

import argparse
import getpass
import os
import sys

from app.application.use_cases.auth import AuthService
from app.bootstrap import Container, build_container
from app.core.config import Settings, get_settings
from app.domain.errors import DomainError
from app.infrastructure.db.repositories.identity import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.seed import seed_demo_catalog


def _read_password(args: argparse.Namespace) -> str:
    if args.password_env:
        value = os.environ.get(args.password_env)
        if not value:
            raise SystemExit(f"Environment variable {args.password_env} is not set or empty.")
        return value
    if not sys.stdin.isatty():
        raise SystemExit(
            "No TTY: pass --password-env VAR to supply the password non-interactively."
        )
    first = getpass.getpass("New admin password (min 12 chars): ")
    if first != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    return first


def create_admin(args: argparse.Namespace, container: Container) -> int:
    password = _read_password(args)
    with container.session_factory() as session:
        service = AuthService(
            users=SqlAlchemyUserRepository(session),
            sessions=SqlAlchemySessionRepository(session),
            audit=SqlAlchemyAuditLogRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
            hasher=container.password_hasher,
            rate_limiter=container.rate_limiter,
            policy=container.auth_policy,
        )
        try:
            user = service.create_admin(
                email=args.email,
                password=password,
                full_name=args.name,
                promote_existing=args.promote,
            )
        except DomainError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    print(f"Owner account ready: {user.email} (roles: {', '.join(sorted(user.roles))})")
    return 0


def seed_demo(args: argparse.Namespace, container: Container) -> int:
    settings = container.settings
    if settings.targets_production_data:
        print(
            "Refusing to seed: this process targets production data "
            f"(APP_ENV={settings.app_env}, NEON_BRANCH={settings.neon_branch}).",
            file=sys.stderr,
        )
        return 2
    if settings.app_env not in ("development", "test") and not args.allow_staging:
        print("Refusing to seed outside development/test (use --allow-staging).", file=sys.stderr)
        return 2
    with container.session_factory() as session:
        result = seed_demo_catalog(session)
    print(
        f"Demo catalogue ready: {result.categories} categories, {result.products} products "
        f"({result.created} created, {result.updated} refreshed)."
    )
    return 0


def main(argv: list[str] | None = None, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="Create (or promote) the store owner account")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", default="Store Owner")
    admin.add_argument("--password-env", help="Read the password from this environment variable")
    admin.add_argument("--promote", action="store_true", help="Promote an existing user to owner")

    seed = sub.add_parser("seed-demo", help="Insert/refresh labelled demo catalogue data")
    seed.add_argument("--allow-staging", action="store_true")

    args = parser.parse_args(argv)
    container = build_container(settings or get_settings())
    try:
        handler = create_admin if args.command == "create-admin" else seed_demo
        return handler(args, container)
    finally:
        container.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
