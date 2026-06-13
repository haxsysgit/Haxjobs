#!/usr/bin/env python3
"""Archilles Pipeline API — serves live pipeline data as JSON for the dashboard.
Listens on 0.0.0.0:8800. Called by systemd or run directly.

v3.0 — Route handlers split into server/routes/ modules.
"""
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PIPELINE_DIR = "/home/hermes/haxjobs"
DASHBOARD_SOURCE_DIR = os.path.join(PIPELINE_DIR, "dashboard")
DASHBOARD_DIST_DIR = os.path.join(DASHBOARD_SOURCE_DIR, "dist")
DASHBOARD_DIR = DASHBOARD_DIST_DIR if os.path.isdir(DASHBOARD_DIST_DIR) else DASHBOARD_SOURCE_DIR

sys.path.insert(0, PIPELINE_DIR)
import pipeline_db as db
from server.routes.jobs import (
    list_jobs,
    unskip_job,
    approve_job,
    toggle_auto_apply,
    queue_intake,
    review_job_pack,
    generate_job_pack,
)
from server.routes.pack_resources import get_pack_detail
from server.routes.resources import (
    list_packs, serve_pack_file,
    handle_whitelist_get, handle_whitelist_post, handle_whitelist_remove,
    get_profile, save_profile,
    get_discovery, get_activity,
    trigger_pipeline,
)

MIME = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".json": "application/json",
    ".pdf": "application/pdf",
}


class APIHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

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

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ── GET ──

    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)

        # API routes
        if path == "/api/jobs":
            status_filter = qs.get("status", [None])[0]
            jobs = list_jobs()
            if status_filter:
                jobs = [j for j in jobs if j["status"] == status_filter]
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
            # Serve pack files: /api/packs/{pack_dir}/{filename}
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

        elif path == "/api/favorites":
            fav_ids = db.get_favorites()
            all_jobs = list_jobs()
            fav_jobs = [j for j in all_jobs if int(j["id"]) in fav_ids]
            self._json(fav_jobs)

        elif path == "/api/saved-jobs":
            saved = db.get_saved_jobs()
            self._json([{
                "id": s["id"],
                "title": s["title"],
                "company": s["company"],
                "location": s.get("location", ""),
                "notes": s.get("saved_notes", ""),
                "savedAt": s.get("saved_at", ""),
            } for s in saved])

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

        elif path == "/api/whitelist":
            self._json(handle_whitelist_get())

        elif path == "/api/companies":
            try:
                import subprocess
                r = subprocess.run(
                    ["python3", os.path.join(PIPELINE_DIR, "pipeline_db.py"), "companies"],
                    capture_output=True, text=True, timeout=10
                )
                self._json([{"name": l.split("(")[0].strip() if "(" in l else l.strip(),
                            "detail": l} for l in r.stdout.splitlines() if l.strip()])
            except Exception:
                self._json([])

        else:
            # Static dashboard files
            filepath = os.path.join(DASHBOARD_DIR, (path.lstrip("/") or "index.html"))
            if os.path.isfile(filepath):
                ext = os.path.splitext(filepath)[1]
                self._file(filepath, MIME.get(ext, "application/octet-stream"))
            else:
                index = os.path.join(DASHBOARD_DIR, "index.html")
                if os.path.isfile(index):
                    self._file(index, "text/html")
                else:
                    self._json({"error": "not found"}, 404)

    # ── POST ──

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

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

        # Favorites
        elif path == "/api/favorites":
            job_id = body.get("job_id")
            if not job_id:
                self._json({"error": "job_id required"}, 400)
                return
            ok = db.add_favorite(int(job_id))
            self._json({"ok": ok, "job_id": job_id})

        elif path == "/api/favorites/remove":
            job_id = body.get("job_id")
            if not job_id:
                self._json({"error": "job_id required"}, 400)
                return
            db.remove_favorite(int(job_id))
            self._json({"ok": True})

        # Saved jobs
        elif path == "/api/saved-jobs":
            job_id = body.get("job_id")
            if not job_id:
                self._json({"error": "job_id required"}, 400)
                return
            ok = db.save_job(int(job_id), body.get("notes", ""))
            self._json({"ok": ok})

        elif path == "/api/saved-jobs/remove":
            job_id = body.get("job_id")
            if not job_id:
                self._json({"error": "job_id required"}, 400)
                return
            db.unsave_job(int(job_id))
            self._json({"ok": True})

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

        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass  # Silence logs


if __name__ == "__main__":
    db.init()
    port = 8800
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"HaxJobs Pipeline API v3.0 running on http://0.0.0.0:{port}")
    server.serve_forever()
