from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    project_name: str = "HaxJobs API"
    project_version: str = "0.1.0"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )
    openai_api_key: str | None = Field(default=None, repr=False)

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


    @classmethod
    def from_env(cls) -> "Settings":
        return cls(openai_api_key=os.getenv("OPENAI_API_KEY"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
