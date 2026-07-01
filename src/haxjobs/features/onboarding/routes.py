"""Onboarding API routes."""
from fastapi import APIRouter
from .service import get_status

router = APIRouter(tags=["onboarding"])


@router.get("/onboarding/status")
def onboarding_status():
    return get_status()
