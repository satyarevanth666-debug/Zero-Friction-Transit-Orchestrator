"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """Return system operational status and metadata."""
    return {
        "status": "ok",
        "app": "zero-friction-transit",
        "version": "0.1.0",
        "environment": settings.APP_ENV,
        "llm_enabled": settings.LLM_ENABLED,
    }
