"""Artifact writer — run directories, atomic receipt files, local-only output."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_ARTIFACTS_ROOT = Path("state/harness-runs")


class ArtifactWriter:
    """Creates run directories (0700) and writes receipt files (0600) atomically."""

    def __init__(self, root: Path = _DEFAULT_ARTIFACTS_ROOT) -> None:
        self._root = root

    def create_run_dir(self, run_id: str) -> Path:
        run_dir = self._root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        run_dir.chmod(0o700)
        return run_dir

    def write_receipt(self, run_dir: Path, filename: str, content: str | bytes) -> Path:
        """Write one receipt file atomically, mode 0600."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        target = run_dir / filename
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(run_dir), prefix=f".{filename}.")
        try:
            os.write(tmp_fd, content)
            os.fsync(tmp_fd)
        finally:
            os.close(tmp_fd)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, target)
        return target

    def write_all_receipts(
        self,
        run_id: str,
        events: list[Any],
        manifest: dict[str, Any],
        context: dict[str, Any],
        transcript: list[dict[str, str]],
        result: dict[str, Any],
        review_md: str,
    ) -> tuple[Path, list[Path]]:
        """Write all six receipt files. Returns (run_dir, list of written paths)."""
        run_dir = self.create_run_dir(run_id)
        written: list[Path] = []

        # events.jsonl — redacted events
        written.append(
            self.write_receipt(
                run_dir,
                "events.jsonl",
                "\n".join(
                    json.dumps(
                        e.model_dump() if hasattr(e, "model_dump") else e
                    )
                    for e in events
                )
                + "\n",
            )
        )

        # manifest.json
        written.append(
            self.write_receipt(
                run_dir,
                "manifest.json",
                json.dumps(manifest, indent=2, default=str),
            )
        )

        # context.json — local only, contains career/job data
        written.append(
            self.write_receipt(
                run_dir,
                "context.json",
                json.dumps(context, indent=2, default=str),
            )
        )

        # transcript.json — local only, contains model text
        written.append(
            self.write_receipt(
                run_dir,
                "transcript.json",
                json.dumps(transcript, indent=2, default=str),
            )
        )

        # result.json
        written.append(
            self.write_receipt(
                run_dir,
                "result.json",
                json.dumps(result, indent=2, default=str),
            )
        )

        # review.md — human review template
        written.append(
            self.write_receipt(run_dir, "review.md", review_md)
        )

        return run_dir, written

    def stable_manifest_hash(self, run_id: str, started_at: str) -> str:
        """Deterministic manifest content hash for stability verification."""
        raw = f"{run_id}|{started_at}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
