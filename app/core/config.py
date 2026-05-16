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
    ai_model_recruiter: str = "gpt-5.4-mini"
    ai_model_evaluator: str = "gpt-5.4-mini"
    ai_model_verifier: str = "gpt-5.4-mini"
    ai_model_applicant: str = "gpt-5.5"

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            ai_model_recruiter=os.getenv("HAXJOBS_MODEL_RECRUITER", "gpt-5.4-mini"),
            ai_model_evaluator=os.getenv("HAXJOBS_MODEL_EVALUATOR", "gpt-5.4-mini"),
            ai_model_verifier=os.getenv("HAXJOBS_MODEL_VERIFIER", "gpt-5.4-mini"),
            ai_model_applicant=os.getenv("HAXJOBS_MODEL_APPLICANT", "gpt-5.5"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
