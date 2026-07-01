"""Discovery API routes."""
from fastapi import APIRouter
from .service import get_status

router = APIRouter(tags=["discovery"])


@router.get("/discovery/status")
def discovery_status():
    return get_status()
