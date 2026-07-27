"""ProviderConfig — credentials and endpoint from haxjobs.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from haxjobs.config import PROVIDER_CONFIG_PATH


class ProviderConfigError(Exception):
    """Raised when provider config cannot be loaded."""


@dataclass
class ProviderConfig:
    """Credentials and endpoint for one provider."""

    provider: str  # "deepseek"
    model: str  # "deepseek-v4-flash"
    base_url: str  # "https://api.deepseek.com/v1"
    api_key: str  # from haxjobs.toml


def load_provider_config(path: Path | None = None) -> ProviderConfig:
    """Load provider config from haxjobs.toml. Raises ProviderConfigError."""
    if path is None:
        path = PROVIDER_CONFIG_PATH
    try:
        raw = tomllib.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ProviderConfigError(
            f"Provider config not found at {path}. Run 'haxjobs setup' first."
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ProviderConfigError(f"Invalid TOML in {path}: {exc}") from exc

    provider = raw.get("provider", {})
    if "model" not in provider:
        raise ProviderConfigError(
            f"Provider config missing required 'model' key — check {path}"
        )
    return ProviderConfig(
        provider=provider.get("name", "deepseek"),
        model=provider["model"],
        base_url=provider.get("base_url", "https://api.deepseek.com/v1"),
        api_key=provider.get("api_key", ""),
    )
