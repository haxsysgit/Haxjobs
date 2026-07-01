"""Profile API routes."""
from fastapi import APIRouter
from .service import get_profile

router = APIRouter(tags=["profile"])


@router.get("/profile")
def profile():
    return get_profile()
