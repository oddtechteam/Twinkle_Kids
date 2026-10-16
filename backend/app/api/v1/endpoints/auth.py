from fastapi import APIRouter, Request, Response, status

from app.api.deps import AuthServiceDep, CurrentUserDep, RequestContextDep, SettingsDep
from app.api.schemas.auth import LoginIn, RegisterIn, UserOut
from app.api.security import clear_session_cookies, set_session_cookies

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    auth: AuthServiceDep,
    settings: SettingsDep,
    context: RequestContextDep,
    response: Response,
) -> UserOut:
    """Customer self-registration. Always creates a customer; staff accounts are CLI-only."""
    issued = auth.register(
        email=str(body.email),
        password=body.password,
        full_name=body.full_name,
        phone=body.phone,
        context=context,
    )
    set_session_cookies(response, settings, issued)
    return UserOut.of(issued.user)


@router.post("/login", response_model=UserOut)
def login(
    body: LoginIn,
    auth: AuthServiceDep,
    settings: SettingsDep,
    context: RequestContextDep,
    response: Response,
) -> UserOut:
    issued = auth.login(email=str(body.email), password=body.password, context=context)
    set_session_cookies(response, settings, issued)
    return UserOut.of(issued.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(auth: AuthServiceDep, settings: SettingsDep, request: Request) -> Response:
    """Revokes the server-side session (idempotent) and clears the cookies."""
    auth.logout(request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response, settings)
    return response


@router.get("/me", response_model=UserOut)
def me(user: CurrentUserDep) -> UserOut:
    return UserOut.of(user)
