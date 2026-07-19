"""Normalized model types — no provider-specific raw objects here."""

from pydantic import BaseModel, Field


class ModelMessage(BaseModel):
    """One message in a model request."""

    role: str
    content: str


class ModelRequest(BaseModel):
    """A complete model call request — internal messages only."""

    messages: list[ModelMessage]
    max_tokens: int = Field(default=4096, ge=1)


class ModelUsage(BaseModel):
    """Provider-reported token usage."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ModelResponse(BaseModel):
    """Successful model response."""

    text: str
    finish_reason: str
    usage: ModelUsage | None = None
    model: str
    provider: str


class ModelFailure(BaseModel):
    """Model call failure — safe for logging and reporting."""

    error: str
    category: str = "provider_error"
    retryable: bool = False
    model: str = ""
    provider: str = ""

    def safe_summary(self) -> str:
        return f"Model failure [{self.category}]: {self.error}"
