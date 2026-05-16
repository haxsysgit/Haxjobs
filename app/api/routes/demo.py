from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.analysis import AnalyzeDemoRequest, AnalyzeResponse, DemoOptionsResponse
from app.services.demo_fixtures import InvalidDemoFixtureError, get_demo_options
from app.services.workflow import analyze_demo

router = APIRouter(tags=["demo"])


@router.get("/api/demo-options", response_model=DemoOptionsResponse)
def demo_options() -> DemoOptionsResponse:
    return get_demo_options()


@router.post("/api/analyze-demo", response_model=AnalyzeResponse)
def analyze_demo_endpoint(payload: AnalyzeDemoRequest) -> AnalyzeResponse:
    try:
        return analyze_demo(
            cv_fixture_id=payload.cv_fixture,
            jd_fixture_id=payload.jd_fixture,
            mode=payload.mode,
        )
    except InvalidDemoFixtureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
