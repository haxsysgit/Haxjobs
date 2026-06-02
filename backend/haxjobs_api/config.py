from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the HaxJobs API."""

    app_name: str = "haxjobs-api"
    database_url: str = "sqlite:///./data/haxjobs.db"
    frontend_origin: str = "http://localhost:5173"
    data_dir: Path = Path("data")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="HAXJOBS_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
