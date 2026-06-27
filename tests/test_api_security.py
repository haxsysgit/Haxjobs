"""Security regression tests for API server helpers."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import api_server


def test_safe_static_path_allows_normal_file(tmp_path):
    """A normal path under the root should resolve."""
    root = tmp_path / "dist"
    root.mkdir()
    (root / "index.html").write_text("<html></html>")

    result = api_server._safe_static_path("/index.html", str(root))

    assert result is not None
    assert result.endswith("index.html")


def test_safe_static_path_rejects_parent_traversal(tmp_path):
    """../../../etc/passwd style traversal should return None."""
    root = tmp_path / "dist"
    root.mkdir()

    result = api_server._safe_static_path("/../../../etc/passwd", str(root))

    assert result is None


def test_safe_static_path_rejects_encoded_parent_traversal(tmp_path):
    """URL-encoded traversal should be decoded before path containment."""
    root = tmp_path / "dist"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("sensitive")

    result = api_server._safe_static_path("/%2e%2e/secret.txt", str(root))

    assert result is None


def test_safe_static_path_rejects_double_dot_only_path(tmp_path):
    """A path that is just '..' should be rejected."""
    root = tmp_path / "dist"
    root.mkdir()

    result = api_server._safe_static_path("/..", str(root))

    assert result is None


def test_safe_static_path_allows_deep_nested_file(tmp_path):
    """Nested files within root should resolve fine."""
    root = tmp_path / "dist"
    nested = root / "assets" / "js"
    nested.mkdir(parents=True)
    (nested / "bundle.js").write_text("console.log(1)")

    result = api_server._safe_static_path("/assets/js/bundle.js", str(root))

    assert result is not None
    assert result.endswith("bundle.js")


def make_request(headers: dict[str, str], body: bytes = b""):
    return SimpleNamespace(headers=headers, rfile=BytesIO(body))


def test_read_json_body_returns_structured_error_for_bad_content_length():
    request = make_request({"Content-Length": "not-a-number"})

    body, status, error = api_server._read_json_body(request)

    assert body == {}
    assert status == 400
    assert error == "invalid Content-Length"


def test_read_json_body_returns_structured_error_for_bad_utf8():
    request = make_request({"Content-Length": "1"}, b"\xff")

    body, status, error = api_server._read_json_body(request)

    assert body == {}
    assert status == 400
    assert error == "request body must be valid UTF-8"


def test_read_json_body_returns_structured_error_for_invalid_json():
    request = make_request({"Content-Length": "7"}, b"{ nope")

    body, status, error = api_server._read_json_body(request)

    assert body == {}
    assert status == 400
    assert error == "invalid JSON in request body"


def test_read_json_body_parses_valid_json():
    request = make_request({"Content-Length": "13"}, b'{"ok": true}')

    body, status, error = api_server._read_json_body(request)

    assert body == {"ok": True}
    assert status is None
    assert error is None


def make_handler(headers: dict[str, str], client_host: str):
    return SimpleNamespace(headers=headers, client_address=(client_host, 12345))


def check_auth(handler) -> bool:
    return api_server.APIHandler._check_auth(handler)  # type: ignore[reportArgumentType]


def test_check_auth_allows_loopback_when_token_unset(monkeypatch):
    monkeypatch.setattr(api_server, "API_TOKEN", None)
    handler = make_handler({}, "127.0.0.1")

    assert check_auth(handler) is True


def test_check_auth_rejects_remote_when_token_unset(monkeypatch):
    monkeypatch.setattr(api_server, "API_TOKEN", None)
    handler = make_handler({}, "203.0.113.10")

    assert check_auth(handler) is False


def test_check_auth_accepts_bearer_token(monkeypatch):
    monkeypatch.setattr(api_server, "API_TOKEN", "secret-token")
    handler = make_handler({"Authorization": "Bearer secret-token"}, "203.0.113.10")

    assert check_auth(handler) is True


def test_check_auth_accepts_custom_token_header(monkeypatch):
    monkeypatch.setattr(api_server, "API_TOKEN", "secret-token")
    handler = make_handler({"X-HaxJobs-Token": "secret-token"}, "203.0.113.10")

    assert check_auth(handler) is True


def test_check_auth_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr(api_server, "API_TOKEN", "secret-token")
    handler = make_handler({"Authorization": "Bearer wrong"}, "127.0.0.1")

    assert check_auth(handler) is False
