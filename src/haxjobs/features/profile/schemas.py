"""Profile request/response schemas."""
from pydantic import BaseModel


class ProfileResponse(BaseModel):
    name: str = ""
    email: str = ""
    message: str = "Profile not yet implemented via API"
