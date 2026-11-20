"""Health and other small endpoints (SRS §5.2)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import __version__
from app.config import Settings
from app.models.schemas import HealthResponse, ProvidersStatus

router = APIRouter(prefix="/api", tags=["misc"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(
        version=__version__,
        env=settings.env,
        demo_mode=settings.demo_mode,
        providers=ProvidersStatus(
            groq=settings.groq_configured,
            gemini=settings.gemini_configured,
        ),
    )
