"""Packs API routes."""
from fastapi import APIRouter
from .service import get_pack_status, generate_pack

router = APIRouter(tags=["packs"])


@router.get("/jobs/{job_id}/pack")
def pack_status(job_id: int):
    return get_pack_status(job_id)


@router.post("/jobs/{job_id}/pack")
def create_pack(job_id: int):
    return generate_pack(job_id)
