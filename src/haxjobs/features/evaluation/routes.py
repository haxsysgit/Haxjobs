"""Evaluation API routes."""
from fastapi import APIRouter
from .service import get_status

router = APIRouter(tags=["evaluation"])


@router.get("/evaluation/status")
def evaluation_status():
    return get_status()
