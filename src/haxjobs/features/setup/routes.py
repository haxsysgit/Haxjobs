"""Setup API routes."""
from fastapi import APIRouter
from .service import get_config, save_config, PRESETS
from .schemas import SetupRequest, SetupResponse, SetupStatusResponse, ProviderPreset

router = APIRouter(tags=["setup"])


@router.get("/setup/status")
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


@router.post("/setup/configure")
def configure_provider(req: SetupRequest) -> SetupResponse:
    cfg = save_config(req.provider, req.api_key, req.model, req.base_url)
    return SetupResponse(
        configured=True,
        provider=cfg["provider"]["name"],
        model=cfg["provider"]["model"],
    )
