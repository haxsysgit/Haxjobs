from __future__ import annotations

import os
import subprocess
import sys


def test_profile_path_defaults_to_state_dir():
    from haxjobs.config import PROFILE_PATH, STATE_DIR

    assert PROFILE_PATH == STATE_DIR / "profile.json"


def test_config_candidates_exclude_user_home():
    import haxjobs.config as config

    assert all(".haxjobs" not in str(path) for path in config._CANDIDATES)


def test_profile_path_env_override(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src:."
    env["HAXJOBS_PROFILE"] = str(tmp_path / "custom-profile.json")

    result = subprocess.run(
        [sys.executable, "-c", "from haxjobs.config import PROFILE_PATH; print(PROFILE_PATH)"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.stdout.strip() == env["HAXJOBS_PROFILE"]
