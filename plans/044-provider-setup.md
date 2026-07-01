# Plan 044: Provider setup — first-run API key + model config

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- src/haxjobs/config.py`
> Plan 040 (package structure) and 041 (FastAPI) must be complete.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW (writes one config file to ~/.haxjobs/)
- **Depends on**: 040, 041, 042
- **Category**: direction
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Before the user uploads a CV or discovers jobs, they need to pick an LLM provider and enter an API key. Without this, onboarding fails at the first LLM call. Default is DeepSeek (the user's current provider), but the design supports any OpenAI-compatible API. Config saved to `~/.haxjobs/config.toml` — shared by the native agent (plan 043), onboarding (plan 045), evaluation (plan 048), and discovery tools.

## Current state

- `src/haxjobs/config.py` reads `haxjobs.toml` for app config (role profiles, job search prefs)
- No provider config exists — no `DEEPSEEK_API_KEY` or model selection
- `~/.haxjobs/` directory doesn't exist yet

## Steps

### Step 1: Create ~/.haxjobs/config.toml schema

```toml
# HaxJobs provider configuration
# Written by setup wizard, editable by hand

[provider]
name = "deepseek"           # deepseek | openai | custom
api_key = "sk-..."           # your API key
base_url = "https://api.deepseek.com"  # endpoint URL
model = "deepseek-chat"      # model name
```

The `base_url` + `model` pattern supports any OpenAI-compatible provider: DeepSeek, OpenAI, Groq, Together, local llama.cpp, etc.

### Step 2: Create features/setup/

#### service.py

```python
"""Provider setup business logic."""
import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / ".haxjobs"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "provider": {
        "name": "deepseek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    }
}

PRESETS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4.1", "gpt-5.5"],
    },
}


def get_config() -> dict | None:
    """Load provider config, or None if not set up."""
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def save_config(provider: str, api_key: str, model: str | None = None) -> dict:
    """Save provider config. Returns the saved config dict."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    preset = PRESETS.get(provider, PRESETS["deepseek"])
    config = {
        "provider": {
            "name": provider,
            "api_key": api_key,
            "base_url": preset["base_url"],
            "model": model or preset["models"][0],
        }
    }
    _write_config(config)
    return config


def _write_config(config: dict):
    """Write TOML config, preserving API key safety with 0o600."""
    # ponytail: simple TOML string builder, no dependency
    lines = ["[provider]"]
    for k, v in config["provider"].items():
        lines.append(f'{k} = "{v}"')
    with open(CONFIG_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(CONFIG_PATH, 0o600)  # api key is in here


def is_configured() -> bool:
    return CONFIG_PATH.exists()
```

#### schemas.py

```python
"""Setup request/response schemas."""
from pydantic import BaseModel


class ProviderPreset(BaseModel):
    key: str
    name: str
    models: list[str]


class SetupRequest(BaseModel):
    provider: str         # "deepseek" | "openai"
    api_key: str
    model: str | None = None


class SetupResponse(BaseModel):
    configured: bool
    provider: str
    model: str


class SetupStatusResponse(BaseModel):
    configured: bool
    provider: str | None = None
    presets: list[ProviderPreset] = []
```

#### routes.py

```python
"""Setup API routes."""
from fastapi import APIRouter
from .service import get_config, save_config, PRESETS
from .schemas import SetupRequest, SetupResponse, SetupStatusResponse, ProviderPreset

router = APIRouter(tags=["setup"])


@router.get("/api/setup/status")
def setup_status() -> SetupStatusResponse:
    cfg = get_config()
    presets = [
        ProviderPreset(key=k, name=v["name"], models=v["models"])
        for k, v in PRESETS.items()
    ]
    if cfg:
        return SetupStatusResponse(
            configured=True,
            provider=cfg["provider"]["name"],
            presets=presets,
        )
    return SetupStatusResponse(configured=False, presets=presets)


@router.post("/api/setup/configure")
def configure_provider(req: SetupRequest) -> SetupResponse:
    cfg = save_config(req.provider, req.api_key, req.model)
    return SetupResponse(
        configured=True,
        provider=cfg["provider"]["name"],
        model=cfg["provider"]["model"],
    )
```

### Step 3: Frontend — SetupPage

Create `frontend/src/pages/SetupPage.tsx`:

1. Fetch `GET /api/setup/status` — if configured, redirect to `/`
2. Show provider selector: two cards — DeepSeek (default, highlighted) and OpenAI
3. "Custom" option: manual base_url + model input (collapsed, expand on click)
4. API key input (password field by default, toggle to show)
5. "Connect" button → `POST /api/setup/configure` → redirect to `/onboarding`
6. Simple, clean — one screen, no multi-step

**shadcn components**: Card, Button, Input, Label, RadioGroup (for provider selection)

### Step 4: Wire into app lifecycle

In `src/haxjobs/app.py`, add the setup router alongside others (already handled — `mount_features()` includes all routers).

In `frontend/src/main.tsx` or router setup: on app load, check `/api/setup/status`. If not configured, redirect to `/setup` regardless of current route (except `/setup` itself).

### Step 5: Commit

```bash
git commit -m "add provider setup: first-run API key + model config screen"
uv run pytest -q tests/  # verify no regressions
```

## Done criteria

- [ ] `GET /api/setup/status` returns `{configured: false}` on fresh install
- [ ] `POST /api/setup/configure` saves to `~/.haxjobs/config.toml` with 0o600 permissions
- [ ] Setup page shows provider selector (DeepSeek default, OpenAI option)
- [ ] API key field is masked by default
- [ ] After setup, redirect to `/onboarding`
- [ ] `~/.haxjobs/config.toml` has correct TOML format

## STOP conditions

- `~/.haxjobs/` can't be created — check permissions
- API key validation — don't validate against the provider on setup (takes too long). Validate on first actual use and show error then.
