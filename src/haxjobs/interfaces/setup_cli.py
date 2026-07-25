"""Attended haxjobs setup — writes provider config once, never calls the provider."""

from __future__ import annotations

import os
import sys
import tempfile
from getpass import getpass
from pathlib import Path

import haxjobs.config


def _toml_escape(value: str) -> str:
    """Escape a string value for a TOML basic string."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def _write_atomic(path: Path, content: str) -> None:
    """Write content to path atomically with 0600 permissions."""
    parent = path.parent
    fd, tmp_name = tempfile.mkstemp(dir=str(parent), prefix=".haxjobs-setup-")
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, str(path))


def run_setup() -> None:
    """Interactive provider setup. Reads from stdin, writes provider TOML.

    Asks for provider name, model, base URL, and API key.
    Writes ~/.haxjobs/haxjobs.toml atomically with 0600 permissions.
    """
    haxjobs.config.ensure_runtime_home()

    if haxjobs.config.PROVIDER_CONFIG_PATH.exists():
        print(
            f"Provider config already exists at "
            f"{haxjobs.config.PROVIDER_CONFIG_PATH}"
        )
        answer = input("Overwrite? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Setup cancelled — existing config unchanged.")
            return

    default_name = "deepseek"
    default_model = "deepseek-v4-flash"
    default_base = "https://api.deepseek.com/v1"

    print()
    print("HaxJobs provider setup")
    print("──────────────────────")
    print(f"All data lives under {haxjobs.config.HAXJOBS_HOME}")
    print()

    name = input(f"Provider name [{default_name}]: ").strip()
    if not name:
        name = default_name

    model = input(f"Model [{default_model}]: ").strip()
    if not model:
        model = default_model

    base_url = input(f"Base URL [{default_base}]: ").strip()
    if not base_url:
        base_url = default_base

    api_key = getpass("API key: ").strip()
    if not api_key:
        print("Error: API key must not be empty.", file=sys.stderr)
        sys.exit(1)

    # Build TOML by hand — no dependency on a TOML writer.
    lines = [
        "[provider]\n",
        f'name = "{_toml_escape(name)}"\n',
        f'model = "{_toml_escape(model)}"\n',
        f'base_url = "{_toml_escape(base_url)}"\n',
        f'api_key = "{_toml_escape(api_key)}"\n',
    ]
    content = "".join(lines)

    _write_atomic(haxjobs.config.PROVIDER_CONFIG_PATH, content)
    print()
    print(f"Provider configured — wrote {haxjobs.config.PROVIDER_CONFIG_PATH}")
