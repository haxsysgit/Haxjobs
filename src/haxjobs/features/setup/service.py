"""Provider setup business logic."""
import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / ".haxjobs"
CONFIG_PATH = CONFIG_DIR / "haxjobs.toml"

PRESETS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4.1", "gpt-5.5"],
    },
    "anthropic": {
        "name": "Anthropic (via OpenAI-compatible proxy)",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
    },
    "custom": {
        "name": "Custom (any OpenAI-compatible API)",
        "base_url": "https://api.example.com/v1",
        "models": ["your-model-name"],
    },
}


def get_config() -> dict | None:
    """Load provider config, or None if not set up."""
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def save_config(provider: str, api_key: str, model: str | None = None,
                base_url: str | None = None) -> dict:
    """Save provider config. Returns the saved config dict."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    preset = PRESETS.get(provider)
    if preset is None:
        raise ValueError(f"Unknown provider: {provider}")
    config = {
        "provider": {
            "name": provider,
            "api_key": api_key,
            "base_url": base_url or preset["base_url"],
            "model": model or preset["models"][0],
        }
    }
    _write_config(config)
    return config


def _write_config(config: dict):
    """Write TOML config with 0o600 permissions (API key inside)."""
    # ponytail: hand-rolled TOML writer. Uses repr() for safe string escaping.
    # Replace with tomli-w if key writes ever get complex.
    lines = ["# HaxJobs provider configuration", "[provider]"]
    for k, v in config["provider"].items():
        lines.append(f"{k} = {v!r}")
    with open(CONFIG_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(CONFIG_PATH, 0o600)


def is_configured() -> bool:
    return CONFIG_PATH.exists()
