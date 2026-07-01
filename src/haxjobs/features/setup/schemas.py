"""Setup request/response schemas."""
from pydantic import BaseModel


class ProviderPreset(BaseModel):
    key: str
    name: str
    models: list[str]


class SetupRequest(BaseModel):
    provider: str         # "deepseek" | "openai" | "anthropic" | "custom"
    api_key: str
    model: str | None = None
    base_url: str | None = None


class SetupResponse(BaseModel):
    configured: bool
    provider: str
    model: str


class SetupStatusResponse(BaseModel):
    configured: bool
    provider: str | None = None
    presets: list[ProviderPreset] = []
