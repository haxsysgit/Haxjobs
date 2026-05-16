from __future__ import annotations

from fastapi import FastAPI

from app.core.application import build_app
from app.core.config import get_settings


def create_app() -> FastAPI:
    return build_app(get_settings())


app = create_app()
