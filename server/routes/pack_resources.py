"""Safe pack detail helpers for dashboard review.

Only known markdown pack files are read. Unknown files and path traversal are
blocked so the dashboard can review packs without becoming a filesystem API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_PACK_TEXT_FILES = (
    "fit_report.md",
    "cover_letter.md",
    "field_answers.md",
    "interview_questions.md",
    "telegram_summary.md",
)


def get_pack_detail(pack_dir: str | Path) -> dict[str, Any]:
    """Return metadata plus allowed text files for one pack directory."""
    root = Path(pack_dir)
    if not root.exists() or not root.is_dir():
        return {"ok": False, "error": "pack not found"}

    metadata: dict[str, Any] = {}
    metadata_path = root / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text())
        except json.JSONDecodeError:
            metadata = {"error": "metadata parse failed"}

    files: dict[str, str] = {}
    for filename in ALLOWED_PACK_TEXT_FILES:
        result = read_pack_text_file(root, filename)
        if result.get("ok"):
            files[filename] = result["content"]

    return {
        "ok": True,
        "packDir": str(root),
        "metadata": metadata,
        "files": files,
    }


def read_pack_text_file(pack_dir: str | Path, filename: str) -> dict[str, Any]:
    """Read one allowed pack text file from a pack directory."""
    if filename not in ALLOWED_PACK_TEXT_FILES:
        return {"ok": False, "error": "invalid filename"}

    root = Path(pack_dir)
    path = (root / filename).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return {"ok": False, "error": "invalid filename"}

    if not path.exists() or not path.is_file():
        return {"ok": False, "error": "file not found"}

    return {"ok": True, "filename": filename, "content": path.read_text()}
