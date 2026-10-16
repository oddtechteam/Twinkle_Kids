import importlib.util
from pathlib import Path

from app.core.security import hash_token, new_token, tokens_match
from app.domain.entities.identity import ROLE_PERMISSIONS
from app.infrastructure.auth.passwords import Argon2PasswordHasher
from app.infrastructure.auth.rate_limit import InMemoryRateLimiter

MIGRATION = Path(__file__).resolve().parents[2] / "migrations/versions/20261017_0003_core_schema.py"


def test_argon2_hashes_verify_and_never_store_plaintext() -> None:
    hasher = Argon2PasswordHasher(time_cost=1, memory_cost=8 * 1024, parallelism=1)
    hashed = hasher.hash("a long pass phrase")
    assert hashed.startswith("$argon2id$")
    assert "a long pass phrase" not in hashed
    assert hasher.verify(hashed, "a long pass phrase")
    assert not hasher.verify(hashed, "wrong pass phrase")
    assert not hasher.verify("not-a-hash", "x")
    # Hashes made with weaker parameters are flagged for upgrade on next login.
    assert Argon2PasswordHasher().needs_rehash(hashed)


def test_session_tokens_are_random_and_stored_hashed() -> None:
    a, b = new_token(), new_token()
    assert a != b and len(a) >= 43
    assert hash_token(a) == hash_token(a) != a
    assert len(hash_token(a)) == 64
    assert tokens_match(a, a) and not tokens_match(a, b)


def test_rate_limiter_blocks_after_limit_and_recovers() -> None:
    now = [1000.0]
    limiter = InMemoryRateLimiter(clock=lambda: now[0])
    for _ in range(3):
        assert limiter.hit("k", limit=3, window_seconds=60) is None
    retry = limiter.hit("k", limit=3, window_seconds=60)
    assert retry is not None and 1 <= retry <= 60
    now[0] += 61
    assert limiter.hit("k", limit=3, window_seconds=60) is None
    limiter.reset("k")
    assert limiter.hit("k", limit=1, window_seconds=60) is None


def test_migration_reference_data_matches_domain_roles() -> None:
    spec = importlib.util.spec_from_file_location("migration_0003", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    domain_permissions = {p.value for perms in ROLE_PERMISSIONS.values() for p in perms}
    assert set(module.PERMISSIONS) == domain_permissions
    assert {slug: set(perms) for slug, (_n, _d, perms) in module.ROLES.items()} == {
        role.value: {p.value for p in perms} for role, perms in ROLE_PERMISSIONS.items()
    }
