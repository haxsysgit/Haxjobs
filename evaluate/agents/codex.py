"""Codex adapter — headless evaluation via ``codex exec --output-schema``.

Primary headless adapter. Schema-enforced JSON eliminates all parsing fragility.
Requires Codex installed (``shutil.which("codex")``) with OAuth or ``CODEX_API_KEY``.

Validated in Plan 028: score 62 L2, schema-valid JSON, same result as Hermes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from evaluate.agents.base import BaseAdapter

# JSON Schema for evaluation output — same schema used in Plan 028 testing
EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "fit_verdict": {"type": "string"},
        "level": {"type": "integer", "minimum": 1, "maximum": 4},
        "level_name": {"type": "string"},
        "strongest_matches": {"type": "array", "items": {"type": "string"}},
        "major_gaps": {"type": "array", "items": {"type": "string"}},
        "sponsorship_risk": {"type": "string"},
        "summary": {"type": "string"},
        "decision": {"type": "string"},
    },
    "required": [
        "fit_score", "fit_verdict", "level", "level_name",
        "strongest_matches", "major_gaps", "sponsorship_risk",
        "summary", "decision",
    ],
    "additionalProperties": False,
}


class CodexAdapter(BaseAdapter):
    name = "codex"

    def can_evaluate_headless(self) -> bool:
        return shutil.which("codex") is not None

    def can_evaluate_session(self) -> bool:
        # Codex has an extension model — session-native possible when running inside Codex.
        # ponytail: not yet implemented. Codex session integration is complex (Rust binary).
        return False

    def evaluate_headless(self, prompt: str) -> str | None:
        """Codex headless via ``codex exec --output-schema``.

        Writes schema + output to temp files, cleans up after.
        Schema enforcement guarantees valid JSON — no parsing fragility.
        """
        # Write schema to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf:
            json.dump(EVAL_SCHEMA, sf)
            schema_path = sf.name

        # Temp file for --output-last-message
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as of:
            output_path = of.name

        try:
            result = subprocess.run(
                [
                    "codex", "exec",
                    "--skip-git-repo-check",
                    "--ephemeral",
                    "--sandbox", "read-only",
                    "--output-schema", schema_path,
                    "--output-last-message", output_path,
                    prompt,
                ],
                capture_output=True, text=True, timeout=300,
                env={**os.environ},
                cwd="/tmp",
            )

            if result.returncode != 0:
                # Check stderr for rate-limit signals
                stderr_lower = result.stderr.lower() if result.stderr else ""
                if any(sig in stderr_lower for sig in ("rate limit", "429", "quota")):
                    return None
                return None

            # Read the schema-validated output
            last_msg = Path(output_path).read_text(errors="replace").strip()
            if not last_msg:
                return None

            # Validate it's parseable JSON (schema enforcement guarantees this)
            json.loads(last_msg)
            return last_msg

        except subprocess.TimeoutExpired:
            return None
        except FileNotFoundError:
            return None
        except Exception:
            return None
        finally:
            Path(schema_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
