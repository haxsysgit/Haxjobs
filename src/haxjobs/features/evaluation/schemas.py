"""Evaluation request/response schemas."""
from pydantic import BaseModel


class EvaluationStatusResponse(BaseModel):
    status: str = "idle"
    message: str = "Evaluation not yet implemented via API"
