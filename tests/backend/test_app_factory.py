from app.main import create_app


def test_create_app_mounts_expected_routes() -> None:
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/api/health" in route_paths
    assert "/api/analyze" in route_paths
    assert "/api/generate-application-pack" in route_paths
    assert "/api/demo-options" in route_paths
    assert "/api/analyze-demo" in route_paths
