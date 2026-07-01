"""Decisions API routes."""
from fastapi import APIRouter
from .service import get_decisions, record_decision
from .schemas import DecisionRequest

router = APIRouter(tags=["decisions"])


@router.get("/decisions")
def list_decisions():
    return {"decisions": get_decisions()}


@router.post("/decisions")
def create_decision(data: DecisionRequest):
    return record_decision(data.job_id, data.decision, data.notes)
