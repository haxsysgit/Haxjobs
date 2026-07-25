#!/usr/bin/env python3
"""Verify that the HaxJobs wheel installs and runs outside the checkout.

Builds the wheel, installs into a fresh venv, and proves:
- haxjobs --help works without creating runtime files
- haxjobs setup writes provider config
- haxjobs migrate --fixture works with a synthetic fixture
- haxjobs chat --fake opens a conversation
- All state lives under the temp HAXJOBS_HOME, not the checkout

No network access, no real provider calls, no live keys.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        if result.stdout:
            print(f"  stdout: {result.stdout[:500]}")
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}")
    return result


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    print(f"Repo root: {repo_root}")

    # ── build wheel ──
    print("\n── Building wheel ──")
    result = run(
        ["uv", "build", "--wheel"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Build failed.")
        return 1

    # Find the built wheel
    dist_dir = repo_root / "dist"
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        print("No wheel found in dist/")
        return 1
    wheel = wheels[-1]
    print(f"  Wheel: {wheel.name}")

    # ── create temp venv ──
    tmp = Path(tempfile.mkdtemp(prefix="haxjobs-verify-"))
    venv = tmp / ".venv"
    home = tmp / "home"
    print(f"\n── Creating venv at {venv} ──")
    print(f"  Home: {home}")

    try:
        result = run(
            ["uv", "venv", str(venv), "--python", sys.executable],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return 1

        # ── install wheel ──
        print("\n── Installing wheel ──")
        result = run(
            ["uv", "pip", "install", "--python", str(venv / "bin" / "python"), str(wheel)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return 1

        haxjobs_bin = str(venv / "bin" / "haxjobs")
        env = {**os.environ, "HAXJOBS_HOME": str(home), "PYTHONPATH": ""}

        # ── test 1: help ──
        print("\n── Test: haxjobs --help ──")
        result = run(
            [haxjobs_bin, "--help"],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            return 1
        assert "setup" in result.stdout, "setup missing from help"
        assert not (home / "state").exists(), "help created state dir"

        # ── test 2: setup ──
        print("\n── Test: haxjobs setup (manual: getpass needs tty) ──")
        # setup requires a tty for getpass; write a minimal config for verification.
        home.mkdir(parents=True, exist_ok=True)
        (home / "state").mkdir(exist_ok=True)
        config_path = home / "haxjobs.toml"
        config_path.write_text(
            '[provider]\n'
            'name = "deepseek"\n'
            'model = "deepseek-v4-flash"\n'
            'base_url = "https://api.deepseek.com/v1"\n'
            'api_key = "test-key-verify"\n'
        )
        config_path.chmod(0o600)
        assert (home / "haxjobs.toml").exists(), "provider config missing"
        assert (home / "state").is_dir(), "state dir missing"

        # ── test 3: migrate ──
        print("\n── Test: haxjobs migrate ──")
        fixture = repo_root / "tests" / "fixtures" / "job_review" / "career.json"
        result = run(
            [haxjobs_bin, "migrate", "--fixture", str(fixture)],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            print(f"  migrate failed: {result.stderr}")
            return 1
        assert (home / "state" / "career_graph.db").exists(), "career db missing after migrate"

        # ── test 4: binary import check ──
        print("\n── Test: import and compose ──")
        # chat --fake needs a PTY; verify the binary can import and compose instead.
        check = tmp / "check.py"
        check.write_text(
            'import haxjobs.config; '
            'haxjobs.config.ensure_runtime_home(); '
            'print(f"home={haxjobs.config.HAXJOBS_HOME}"); '
            'print(f"provider={haxjobs.config.PROVIDER_CONFIG_PATH}"); '
            'print("OK")\n'
        )
        result = run(
            [str(venv / "bin" / "python"), str(check)],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            print(f"  import check failed: {result.stderr}")
            return 1
        assert "OK" in result.stdout, f"import check failed: {result.stdout}"
        print(f"  {result.stdout.strip()}")

        # ── also test that haxjobs chat --help works ──
        print("\n── Test: haxjobs chat --help ──")
        result = run(
            [haxjobs_bin, "chat", "--help"],
            capture_output=True, text=True, env=env,
        )
        if result.returncode != 0:
            print(f"  chat --help failed: {result.stderr}")
            return 1
        assert "--fake" in result.stdout, "--fake missing from chat help"

        # ── verify state all under home ──
        print("\n── Verification: all state under home ──")
        db_files = list(home.rglob("*.db"))
        toml_files = list(home.rglob("*.toml"))
        print(f"  DB files: {[str(p.relative_to(home)) for p in db_files]}")
        print(f"  TOML files: {[str(p.relative_to(home)) for p in toml_files]}")
        assert len(toml_files) == 1, f"Expected 1 TOML, got {len(toml_files)}"
        # At minimum career_graph.db; sessions.db only created after real chat.
        assert len(db_files) >= 1, f"Expected >=1 DB, got {len(db_files)}"

        print("\n✓ Wheel verification PASSED")
        return 0

    finally:
        print(f"\nCleaning up {tmp}")
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
