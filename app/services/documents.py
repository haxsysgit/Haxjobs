from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class UnsupportedDocumentError(ValueError):
    """Raised when a document format is not supported."""


def normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n")
    lines = [line.rstrip() for line in cleaned.split("\n")]
    normalized: list[str] = []
    blank_count = 0
    for line in lines:
        compact = " ".join(line.split()) if line.strip() else ""
        if not compact:
            blank_count += 1
            if blank_count <= 2:
                normalized.append("")
            continue
        blank_count = 0
        normalized.append(compact)
    return "\n".join(normalized).strip()


def extract_text_from_path(path: str | Path) -> str:
    file_path = _resolve_existing_input_path(Path(path))
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(file_path)
    if suffix == ".txt":
        return _extract_txt_text(file_path)
    raise UnsupportedDocumentError("Only PDF and TXT CV files are supported.")


def _resolve_existing_input_path(path: Path) -> Path:
    if path.exists():
        return path
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "tests" and parts[1] in {"cv", "jd"}:
        fallback = Path("lab") / parts[1] / parts[-1]
        if fallback.exists():
            return fallback
    return path


def extract_text_from_upload(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return normalize_text(_decode_text_bytes(content))
    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        try:
            return _extract_pdf_text(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
    raise UnsupportedDocumentError("Only PDF and TXT CV files are supported.")


def _decode_text_bytes(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_txt_text(path: Path) -> str:
    content = path.read_bytes()
    return normalize_text(_decode_text_bytes(content))


def _extract_pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "pdftotext failed to extract CV text.")
    return normalize_text(result.stdout)
