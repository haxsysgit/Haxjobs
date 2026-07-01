#!/usr/bin/env python3
"""HaxJobs API — serves pipeline data as JSON for the dashboard.

v3.1 — Path containment, CORS restriction, optional token auth, structured errors.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# ── Config ──

from haxjobs.config import HAXJOBS_HOME as PIPELINE_DIR, DB_PATH
DASHBOARD_SOURCE_DIR = str(PIPELINE_DIR / "dashboard")
DASHBOARD_DIST_DIR = str(PIPELINE_DIR / "dashboard" / "dist")
DASHBOARD_DIR = DASHBOARD_DIST_DIR if os.path.isdir(DASHBOARD_DIST_DIR) else DASHBOARD_SOURCE_DIR

# Bind to loopback by default. Set HAXJOBS_API_HOST=0.0.0.0 only if required.
API_HOST = os.environ.get("HAXJOBS_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("HAXJOBS_API_PORT", "8800"))

# Optional token for mutating POST routes. If set, clients must send
# Authorization: Bearer <token> or X-HaxJobs-Token: <token> on all POSTs.
API_TOKEN = os.environ.get("HAXJOBS_API_TOKEN", "").strip() or None

# Allowed dashboard origins for CORS.
ALLOWED_ORIGINS = frozenset(
    o for o in os.environ.get("HAXJOBS_CORS_ORIGINS", "").split(",") if o
) or frozenset({
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8800",
    "http://localhost:8800",
})

MAX_POST_BODY_BYTES = int(os.environ.get("HAXJOBS_MAX_POST_BODY", "1048576"))  # 1 MiB

sys.path.insert(0, str(PIPELINE_DIR))
import haxjobs.pipeline_db as db
from haxjobs.server.routes.jobs import (
    list_jobs,
    unskip_job,
    approve_job,
    toggle_auto_apply,
    queue_intake,
    review_job_pack,
    generate_job_pack,
)
from haxjobs.server.routes.pack_resources import get_pack_detail
from haxjobs.server.routes.resources import (
    list_packs, serve_pack_file,
    handle_whitelist_get, handle_whitelist_post, handle_whitelist_remove,
    get_profile, save_profile,
    get_discovery, get_activity,
    trigger_pipeline,
)
from haxjobs.server.routes.outreach import (
    list_outreach_jobs, list_outreach_drafts,
    approve_draft, reject_draft,
)

MIME = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".pdf": "application/pdf",
}


# ── Helpers ──

def _parse_json_body(value: str | None) -> tuple[dict, str | None]:
    """Parse JSON POST body safely. Returns (parsed_dict, error_message)."""
    if not value or not value.strip():
        return {}, None
    if len(value) > MAX_POST_BODY_BYTES:
        return {}, "request body too large"
    try:
        return json.loads(value), None
    except (json.JSONDecodeError, ValueError):
        return {}, "invalid JSON in request body"


def _safe_static_path(requested: str, root_dir: str) -> str | None:
    """Resolve requested path and reject traversal outside root_dir."""
    resolved_root = Path(root_dir).resolve()
    decoded_path = unquote(requested)
    filepath = (resolved_root / decoded_path.lstrip("/")).resolve()
    try:
        filepath.relative_to(resolved_root)
    except ValueError:
        return None
    return str(filepath)


def _read_json_body(request_handler) -> tuple[dict, int | None, str | None]:
    """Read and parse a JSON request body from a BaseHTTPRequestHandler.

    Returns (body, status_code, error). status_code and error are None when
    parsing succeeds.
    """
    raw_length = request_handler.headers.get("Content-Length", "0")
    try:
        body_length = int(raw_length)
    except (TypeError, ValueError):
        return {}, 400, "invalid Content-Length"

    if body_length > MAX_POST_BODY_BYTES:
        return {}, 413, "request body too large"

    if body_length <= 0:
        return {}, None, None

    try:
        raw_body = request_handler.rfile.read(body_length).decode("utf-8")
    except UnicodeDecodeError:
        return {}, 400, "request body must be valid UTF-8"

    parsed_body, parse_error = _parse_json_body(raw_body)
    if parse_error:
        return {}, 400, parse_error
    return parsed_body, None, None


# ── Handler ──

class APIHandler(BaseHTTPRequestHandler):

    # ── Response helpers ──

    def _cors_origin(self):
        """Return the allowed origin matching the request, or None."""
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            return origin
        # Allow same-origin requests (no Origin header)
        if not origin:
            return None
        # Return the first allowed origin for OPTIONS preflight
        return None

    def _cors(self):
        """Send CORS headers for allowed origins."""
        origin = self._cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-HaxJobs-Token")

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _file(self, path, content_type):
        if not os.path.isfile(path):
            return False
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self._cors()
        self.end_headers()
        with open(path, "rb") as f:
            self.wfile.write(f.read())
        return True

    # ── Auth ──

    def _check_auth(self) -> bool:
        """Return True if the request is authorized for mutating operations.

        If API_TOKEN is not set, only local (loopback) clients are allowed.
        If API_TOKEN IS set, clients must pass a valid Bearer or X-HaxJobs-Token.
        """
        if API_TOKEN is None:
            # Token not configured — allow only loopback clients
            client_host = self.client_address[0] if self.client_address else ""
            return client_host in ("127.0.0.1", "::1", "localhost")

        # Token configured — require valid token
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:] == API_TOKEN:
            return True
        custom_token = self.headers.get("X-HaxJobs-Token", "")
        if custom_token == API_TOKEN:
            return True
        return False

    def _reject_unauthorized(self):
        self._json({"ok": False, "error": "unauthorized"}, 401)

    # ── HTTP methods ──

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ── GET ──

    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        # API routes — all GETs are read-only, no auth required

        if path == "/api/jobs":
            status_filter = qs.get("status", [None])[0]
            offset_str = qs.get("offset", ["0"])[0]
            limit_str = qs.get("limit", [None])[0]
            try:
                offset = max(0, int(offset_str))
            except (ValueError, TypeError):
                offset = 0
            try:
                limit = int(limit_str) if limit_str else None
            except (ValueError, TypeError):
                limit = None
            jobs = list_jobs(status_filter=status_filter, offset=offset, limit=limit)
            self._json(jobs)

        elif path == "/api/packs":
            self._json(list_packs())

        elif path == "/api/pack-detail":
            pack_dir = qs.get("dir", [""])[0]
            if not pack_dir:
                self._json({"ok": False, "error": "dir required"}, 400)
            else:
                detail = get_pack_detail(pack_dir)
                self._json(detail, 200 if detail.get("ok") else 404)

        elif path.startswith("/api/packs/"):
            parts = path.split("/")
            if len(parts) >= 5:
                filename = parts[-1]
                pack_dir = "/".join(parts[3:-1])
                filepath = serve_pack_file(pack_dir, filename)
                if filepath:
                    ext = os.path.splitext(filepath)[1]
                    self._file(filepath, MIME.get(ext, "application/octet-stream"))
                else:
                    self._json({"error": "file not found"}, 404)
            else:
                self._json({"error": "invalid path"}, 400)

        elif path == "/api/profile":
            self._json(get_profile())

        elif path == "/api/discovery":
            self._json(get_discovery())

        elif path == "/api/stats":
            self._json(db.get_stats())

        elif path == "/api/status":
            s = db.get_stats()
            self._json({
                "jobs": s["total_jobs"],
                "pending": s["pending"],
                "packs": len(list_packs()),
                "discovery": get_discovery(),
            })

        elif path == "/api/activity":
            self._json(get_activity())

        elif path == "/api/outreach/jobs":
            self._json(list_outreach_jobs())

        elif path == "/api/outreach/drafts":
            job_id = qs.get("job_id", [None])[0]
            self._json(list_outreach_drafts(int(job_id) if job_id else None))

        elif path == "/api/whitelist":
            self._json(handle_whitelist_get())

        elif path == "/api/companies":
            try:
                import subprocess
                r = subprocess.run(
                    ["python3", str(PIPELINE_DIR / "pipeline_db.py"), "companies"],
                    capture_output=True, text=True, timeout=10
                )
                self._json([{"name": l.split("(")[0].strip() if "(" in l else l.strip(),
                            "detail": l} for l in r.stdout.splitlines() if l.strip()])
            except Exception:
                self._json([])

        else:
            # Static dashboard files — reject traversal before SPA fallback.
            filepath = _safe_static_path(path, DASHBOARD_DIR)
            if filepath is None:
                self._json({"error": "not found"}, 404)
                return
            if os.path.isfile(filepath):
                ext = os.path.splitext(filepath)[1]
                self._file(filepath, MIME.get(ext, "application/octet-stream"))
            else:
                index = _safe_static_path("index.html", DASHBOARD_DIR)
                if index and os.path.isfile(index):
                    self._file(index, "text/html")
                else:
                    self._json({"error": "not found"}, 404)

    # ── POST ──

    def do_POST(self):
        path = urlparse(self.path).path

        # Auth check for all mutating routes
        if not self._check_auth():
            self._reject_unauthorized()
            return

        # Safely parse the body
        body, error_status, parse_error = _read_json_body(self)
        if parse_error:
            self._json({"ok": False, "error": parse_error}, error_status or 400)
            return

        # Job actions
        if path == "/api/trigger":
            status, data = trigger_pipeline()
            self._json(data, status)

        elif path == "/api/queue":
            status, data = queue_intake(body)
            self._json(data, status)

        elif path == "/api/jobs/unskip":
            status, data = unskip_job(body)
            self._json(data, status)

        elif path == "/api/jobs/approve":
            status, data = approve_job(body)
            self._json(data, status)

        elif path == "/api/jobs/auto-apply":
            status, data = toggle_auto_apply(body)
            self._json(data, status)

        elif path == "/api/jobs/review-pack":
            status, data = review_job_pack(body)
            self._json(data, status)

        elif path == "/api/jobs/generate-pack":
            status, data = generate_job_pack(body)
            self._json(data, status)

        # Whitelist
        elif path == "/api/whitelist":
            status, data = handle_whitelist_post(body)
            self._json(data, status)

        elif path == "/api/whitelist/remove":
            status, data = handle_whitelist_remove(body)
            self._json(data, status)

        # Profile
        elif path == "/api/profile/save":
            status, data = save_profile(body)
            self._json(data, status)

        # Outreach
        elif path == "/api/outreach/approve":
            draft_id = body.get("draft_id")
            if not draft_id:
                self._json({"ok": False, "error": "draft_id required"}, 400)
            else:
                self._json(approve_draft(int(draft_id)))

        elif path == "/api/outreach/reject":
            draft_id = body.get("draft_id")
            reason = body.get("reason", "")
            if not draft_id:
                self._json({"ok": False, "error": "draft_id required"}, 400)
            else:
                self._json(reject_draft(int(draft_id), reason))

        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass  # Silence logs


if __name__ == "__main__":
    db.init()
    server = HTTPServer((API_HOST, API_PORT), APIHandler)
    print(f"HaxJobs Pipeline API v3.1 running on http://{API_HOST}:{API_PORT}")
    if API_TOKEN:
        print("  Token auth:  enabled")
    else:
        print("  Auth:        loopback-only")
    print("  CORS:        %d allowed origins" % len(ALLOWED_ORIGINS))
    server.serve_forever()
