from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(ok=True, llm_configured=settings.llm_configured)
