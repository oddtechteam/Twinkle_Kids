from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.bootstrap import Container
from app.domain.entities.identity import Role
from app.infrastructure.db.models.identity import AuditLogModel, UserModel, UserSessionModel
from tests.conftest import PASSWORD, create_user, csrf, login

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


def register(client: TestClient, email: str = "asha@twinklekids.in", **extra: object) -> object:
    body = {"email": email, "password": PASSWORD, "full_name": "Asha Rao", **extra}
    return client.post(REGISTER, json=body)


def test_register_creates_customer_with_hashed_password_and_session_cookie(
    client: TestClient, container: Container
) -> None:
    response = register(client, email="  Asha@TwinkleKids.in ")
    assert response.status_code == 201, response.text  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert body["email"] == "asha@twinklekids.in"
    assert body["roles"] == ["customer"]
    assert body["is_staff"] is False
    assert not {"password", "password_hash"} & body.keys()

    cookies = response.headers.get_list("set-cookie")  # type: ignore[attr-defined]
    session_cookie = next(c for c in cookies if c.startswith("tk_session="))
    csrf_cookie = next(c for c in cookies if c.startswith("tk_csrf="))
    assert "HttpOnly" in session_cookie and "SameSite=lax" in session_cookie
    assert "HttpOnly" not in csrf_cookie  # readable by the frontend for the CSRF header

    with container.session_factory() as session:
        user = session.scalars(select(UserModel)).one()
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
        token = client.cookies.get("tk_session")
        stored = session.scalars(select(UserSessionModel.token_hash)).one()
        assert stored != token and len(stored) == 64  # only the hash is stored

    me = client.get(ME)
    assert me.status_code == 200 and me.json()["email"] == "asha@twinklekids.in"


def test_register_rejects_duplicates_weak_passwords_and_role_injection(client: TestClient) -> None:
    assert register(client).status_code == 201  # type: ignore[attr-defined]
    assert register(client).status_code == 409  # type: ignore[attr-defined]
    weak = client.post(
        REGISTER, json={"email": "b@twinklekids.in", "password": "short", "full_name": "B"}
    )
    assert weak.status_code == 422
    injected = register(client, email="c@twinklekids.in", roles=["owner"])
    assert injected.status_code == 422  # extra fields are forbidden: no public admin sign-up
    bad_email = client.post(
        REGISTER, json={"email": "nope", "password": PASSWORD, "full_name": "X"}
    )
    assert bad_email.status_code == 422


def test_login_logout_and_session_invalidation(client: TestClient, container: Container) -> None:
    user = create_user(container, email="mira@twinklekids.in", password=PASSWORD)

    wrong = client.post(LOGIN, json={"email": user.email, "password": "wrong password here"})
    unknown = client.post(LOGIN, json={"email": "ghost@twinklekids.in", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Invalid email or password."}

    login(client, user.email, PASSWORD)
    old_token = client.cookies.get("tk_session")
    assert client.get(ME).status_code == 200

    # Logout needs the CSRF header (double-submit) because it is a cookie-authenticated POST.
    assert client.post(LOGOUT).status_code == 403
    assert client.post(LOGOUT, headers=csrf(client)).status_code == 204
    assert client.get(ME).status_code == 401

    # The old token is revoked server-side: replaying it does not work.
    client.cookies.set("tk_session", old_token or "")
    assert client.get(ME).status_code == 401
    with container.session_factory() as session:
        assert (
            session.scalar(select(func.count()).where(UserSessionModel.revoked_at.is_not(None)))
            == 1
        )
        actions = set(session.scalars(select(AuditLogModel.action)))
    assert "user.login" in actions


def test_login_is_rate_limited_per_account(client: TestClient, container: Container) -> None:
    user = create_user(container, email="ravi@twinklekids.in", password=PASSWORD)
    for _ in range(5):
        client.post(LOGIN, json={"email": user.email, "password": "wrong password here"})
    blocked = client.post(LOGIN, json={"email": user.email, "password": PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_inactive_users_cannot_sign_in(client: TestClient, container: Container) -> None:
    user = create_user(container, email="gone@twinklekids.in", password=PASSWORD)
    with container.session_factory() as session:
        session.get(UserModel, user.id).is_active = False  # type: ignore[union-attr]
        session.commit()
    assert client.post(LOGIN, json={"email": user.email, "password": PASSWORD}).status_code == 401


def test_cross_site_requests_are_blocked(client: TestClient) -> None:
    hostile = client.post(
        REGISTER,
        json={"email": "x@twinklekids.in", "password": PASSWORD, "full_name": "X"},
        headers={"Origin": "https://evil.example"},
    )
    assert hostile.status_code == 403
    trusted = client.post(
        REGISTER,
        json={"email": "y@twinklekids.in", "password": PASSWORD, "full_name": "Y"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert trusted.status_code == 201


def test_admin_routes_require_staff_permissions(client: TestClient, container: Container) -> None:
    assert client.get("/api/v1/admin/me").status_code == 401

    customer = create_user(container, Role.CUSTOMER)
    login(client, customer.email)
    assert client.get("/api/v1/admin/me").status_code == 403
    assert (
        client.post(
            "/api/v1/admin/categories", json={"name": "X"}, headers=csrf(client)
        ).status_code
        == 403
    )

    client.post(LOGOUT, headers=csrf(client))
    orders_only = create_user(container, Role.ORDER_MANAGER)
    login(client, orders_only.email)
    me = client.get("/api/v1/admin/me")
    assert me.status_code == 200
    assert "orders:manage" in me.json()["permissions"]
    # Staff, but without catalog:manage -> still forbidden from catalogue writes.
    assert (
        client.post(
            "/api/v1/admin/categories", json={"name": "X"}, headers=csrf(client)
        ).status_code
        == 403
    )

    client.post(LOGOUT, headers=csrf(client))
    owner = create_user(container, Role.OWNER)
    login(client, owner.email)
    me = client.get("/api/v1/admin/me").json()
    assert me["is_staff"] and len(me["permissions"]) == 10
