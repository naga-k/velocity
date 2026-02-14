"""Health check endpoint."""

from fastapi import APIRouter

from app.config import settings
from app.models import HealthResponse

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    status = "ok" if settings.anthropic_configured else "degraded"
    return HealthResponse(
        status=status,
        anthropic_configured=settings.anthropic_configured,
    )
