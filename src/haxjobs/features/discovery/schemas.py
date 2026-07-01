"""Discovery request/response schemas."""
from pydantic import BaseModel


class DiscoveryStatusResponse(BaseModel):
    status: str = "idle"
    message: str = "Discovery not yet implemented via API"
