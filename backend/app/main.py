"""FastAPI entry point: `uvicorn app.main:app --host 127.0.0.1 --port 8000`."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import install_error_handlers
from app.api.routes_misc import router as misc_router
from app.config import Settings, get_settings
from app.net import use_system_trust_store

log = logging.getLogger("litlens")


def _startup_checks(settings: Settings) -> None:
    """Warn loudly about risky or incomplete configuration. Never logs secrets."""
    if not settings.host_is_loopback:
        log.warning(
            "HOST=%s exposes the API to your network (SECURITY N-1). "
            "Use 127.0.0.1 unless you really need this.",
            settings.host,
        )
    if not settings.groq_configured and not settings.demo_mode:
        log.warning("GROQ_API_KEY is not set: live reviews will fail.")
    if not settings.gemini_configured:
        log.warning(
            "Gemini fallback disabled (GEMINI_API_KEY or GEMINI_MODEL not set)."
        )
    if not settings.arxiv_contact:
        log.warning(
            "ARXIV_CONTACT is not set: arXiv asks for a contact in the User-Agent."
        )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    log.info(
        "LitLens %s starting: env=%s demo_mode=%s data_dir=%s",
        __version__,
        settings.env,
        settings.demo_mode,
        settings.data_dir,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    use_system_trust_store()
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        _startup_checks(settings)
        yield

    app = FastAPI(
        title="LitLens API",
        version=__version__,
        lifespan=lifespan,
        # SECURITY N-3: interactive docs only in dev.
        docs_url="/docs" if settings.is_dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_dev else None,
    )
    app.state.settings = settings

    # SECURITY N-2: explicit origins only, never "*".
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    install_error_handlers(app)
    app.include_router(misc_router)
    return app


app = create_app()
