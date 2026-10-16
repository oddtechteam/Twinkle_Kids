import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.security import csrf_protection
from app.api.v1.router import api_router
from app.bootstrap import Container, build_container
from app.core.config import Settings, get_settings
from app.core.version import __version__


def create_app(settings: Settings | None = None, *, container: Container | None = None) -> FastAPI:
    settings = settings or (container.settings if container else get_settings())
    container = container or build_container(settings)
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
    # SDK wire logs can include signed request headers; keep them out of debug output.
    for noisy in ("botocore", "boto3", "urllib3", "s3transfer", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        container.dispose()

    docs_enabled = settings.show_docs
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Twinkle Kids e-commerce API — Cute Styles for Little Smiles.",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )

    app.state.container = container

    prefix = settings.api_v1_prefix
    app.middleware("http")(
        csrf_protection(
            settings, exempt_paths=frozenset({f"{prefix}/auth/login", f"{prefix}/auth/register"})
        )
    )
    # Explicit trusted origins only (credentials are allowed, so "*" is never used).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
