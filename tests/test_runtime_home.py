"""Config resolves to ~/.haxjobs by default, HAXJOBS_HOME overrides."""

import importlib
import os
import subprocess
import sys
from pathlib import Path

import haxjobs.config


def _reload_config(env_override: dict | None = None) -> None:
    """Reload config module with optional env overrides."""
    importlib.reload(haxjobs.config)
    if env_override:
        for k, v in env_override.items():
            os.environ[k] = v


def test_default_home_is_dot_haxjobs():
    """When HAXJOBS_HOME is unset, home resolves to ~/.haxjobs."""
    importlib.reload(haxjobs.config)
    expected = Path.home() / ".haxjobs"
    assert haxjobs.config.HAXJOBS_HOME == expected


def test_home_from_env(tmp_path):
    """HAXJOBS_HOME env var overrides the default."""
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    try:
        importlib.reload(haxjobs.config)
        assert haxjobs.config.HAXJOBS_HOME == tmp_path.resolve()
    finally:
        os.environ.pop("HAXJOBS_HOME", None)


def test_state_dir_under_home(tmp_path):
    """STATE_DIR is under HAXJOBS_HOME."""
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    try:
        importlib.reload(haxjobs.config)
        assert haxjobs.config.STATE_DIR == tmp_path.resolve() / "state"
    finally:
        os.environ.pop("HAXJOBS_HOME", None)


def test_provider_config_path_under_home(tmp_path):
    """PROVIDER_CONFIG_PATH is HAXJOBS_HOME / haxjobs.toml."""
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    try:
        importlib.reload(haxjobs.config)
        assert haxjobs.config.PROVIDER_CONFIG_PATH == tmp_path.resolve() / "haxjobs.toml"
    finally:
        os.environ.pop("HAXJOBS_HOME", None)


def test_career_db_env_override(tmp_path):
    """HAXJOBS_CAREER_DB overrides the default path."""
    db = tmp_path / "custom.db"
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    os.environ["HAXJOBS_CAREER_DB"] = str(db)
    try:
        importlib.reload(haxjobs.config)
        assert haxjobs.config.CAREER_DB_PATH == db
    finally:
        os.environ.pop("HAXJOBS_HOME", None)
        os.environ.pop("HAXJOBS_CAREER_DB", None)


def test_session_db_env_override(tmp_path):
    """HAXJOBS_SESSION_DB overrides the default path."""
    db = tmp_path / "custom_sessions.db"
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    os.environ["HAXJOBS_SESSION_DB"] = str(db)
    try:
        importlib.reload(haxjobs.config)
        assert haxjobs.config.SESSION_DB_PATH == db
    finally:
        os.environ.pop("HAXJOBS_HOME", None)
        os.environ.pop("HAXJOBS_SESSION_DB", None)


def test_ensure_runtime_home_creates_dirs(tmp_path):
    """ensure_runtime_home() creates home and state dirs."""
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    try:
        importlib.reload(haxjobs.config)
        haxjobs.config.ensure_runtime_home()
        assert haxjobs.config.HAXJOBS_HOME.is_dir()
        assert haxjobs.config.STATE_DIR.is_dir()
    finally:
        os.environ.pop("HAXJOBS_HOME", None)


def test_ensure_runtime_home_idempotent(tmp_path):
    """Calling ensure_runtime_home() twice is safe."""
    os.environ["HAXJOBS_HOME"] = str(tmp_path)
    try:
        importlib.reload(haxjobs.config)
        haxjobs.config.ensure_runtime_home()
        haxjobs.config.ensure_runtime_home()
        assert haxjobs.config.HAXJOBS_HOME.is_dir()
        assert haxjobs.config.STATE_DIR.is_dir()
    finally:
        os.environ.pop("HAXJOBS_HOME", None)


def test_help_does_not_create_home():
    """haxjobs --help must not create ~/.haxjobs."""
    test_home = "/tmp/haxjobs-test-nonexistent-help"
    env = {**os.environ, "HAXJOBS_HOME": test_home, "PYTHONPATH": "src:."}
    tmp = subprocess.run(
        [sys.executable, "-m", "haxjobs", "--help"],
        capture_output=True,
        text=True,
        cwd="/",
        env=env,
    )
    assert tmp.returncode == 0
    assert "setup" in tmp.stdout
    assert not Path(test_home).exists()


def test_fake_chat_no_provider_ok(tmp_path):
    """Fake chat should not require provider config."""
    env = {**os.environ, "HAXJOBS_HOME": str(tmp_path), "PYTHONPATH": "src:."}
    tmp = subprocess.run(
        [sys.executable, "-m", "haxjobs", "chat", "--fake"],
        capture_output=True,
        text=True,
        env=env,
    )
    stderr_lower = tmp.stderr.lower()
    assert "no provider" not in stderr_lower
