from __future__ import annotations

import os
from pathlib import Path


class UnsafeDocumentPathError(ValueError):
    """Raised when a requested document path escapes the storage directory."""


class DocumentStorage:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        configured_root = root_dir or os.getenv("HAXJOBS_DOCUMENT_STORAGE_DIR") or "data/documents"
        self.root_dir = Path(configured_root).expanduser().resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def resolve_safe_path(self, relative_path: str) -> Path:
        candidate = (self.root_dir / relative_path).resolve()
        if not candidate.is_relative_to(self.root_dir):
            raise UnsafeDocumentPathError(f"Document path is outside document storage: {relative_path}")
        return candidate

    def write_text(self, relative_path: str, content: str) -> Path:
        target = self.resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target
