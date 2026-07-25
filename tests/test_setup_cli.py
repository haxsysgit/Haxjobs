"""Tests for haxjobs setup CLI — provider config writing."""

import os
from pathlib import Path
from unittest import mock

import pytest

import haxjobs.config
from haxjobs.interfaces.setup_cli import run_setup


def _reload_config(home: Path) -> None:
    import importlib
    os.environ["HAXJOBS_HOME"] = str(home)
    importlib.reload(haxjobs.config)
    # Also reload setup_cli so it picks up the new config module references.
    import haxjobs.interfaces.setup_cli as sc
    importlib.reload(sc)


@pytest.fixture
def temp_home(tmp_path):
    """Set HAXJOBS_HOME to a temp dir for the test."""
    orig = os.environ.get("HAXJOBS_HOME")
    _reload_config(tmp_path)
    yield tmp_path
    if orig is not None:
        os.environ["HAXJOBS_HOME"] = orig
    else:
        os.environ.pop("HAXJOBS_HOME", None)
    import importlib
    importlib.reload(haxjobs.config)
    import haxjobs.interfaces.setup_cli as sc
    importlib.reload(sc)


def test_setup_writes_provider_config(temp_home):
    """setup writes provider TOML with expected fields."""
    with (
        mock.patch("builtins.input", side_effect=["", "", "", ""]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value="sk-test-key"),
    ):
        run_setup()

    assert haxjobs.config.PROVIDER_CONFIG_PATH.exists()
    content = haxjobs.config.PROVIDER_CONFIG_PATH.read_text()
    assert 'name = "deepseek"' in content
    assert 'model = "deepseek-v4-flash"' in content
    assert 'base_url = "https://api.deepseek.com/v1"' in content
    assert 'api_key = "sk-test-key"' in content

    stat = haxjobs.config.PROVIDER_CONFIG_PATH.stat()
    assert stat.st_mode & 0o777 == 0o600


def test_setup_creates_runtime_home(temp_home):
    """setup creates home and state directories."""
    with (
        mock.patch("builtins.input", side_effect=["", "", "", ""]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value="key"),
    ):
        run_setup()

    assert haxjobs.config.HAXJOBS_HOME.is_dir()
    assert haxjobs.config.STATE_DIR.is_dir()


def test_setup_rejects_empty_key(temp_home):
    """setup exits when API key is empty."""
    with pytest.raises(SystemExit):
        with (
            mock.patch("builtins.input", side_effect=["", "", "", ""]),
            mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value=""),
        ):
            run_setup()

    assert not haxjobs.config.PROVIDER_CONFIG_PATH.exists()


def test_setup_declines_overwrite(temp_home):
    """setup asks before overwriting and keeps existing config on decline."""
    with (
        mock.patch("builtins.input", side_effect=["", "", "", ""]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value="first-key"),
    ):
        run_setup()

    original = haxjobs.config.PROVIDER_CONFIG_PATH.read_text()
    assert 'api_key = "first-key"' in original

    with (
        mock.patch("builtins.input", side_effect=["n"]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value=""),
    ):
        run_setup()

    current = haxjobs.config.PROVIDER_CONFIG_PATH.read_text()
    assert current == original


def test_setup_overwrites_when_confirmed(temp_home):
    """setup overwrites existing config when user confirms."""
    with (
        mock.patch("builtins.input", side_effect=["", "", "", ""]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value="first-key"),
    ):
        run_setup()

    with (
        mock.patch("builtins.input", side_effect=["y", "", "", "", ""]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value="second-key"),
    ):
        run_setup()

    content = haxjobs.config.PROVIDER_CONFIG_PATH.read_text()
    assert 'api_key = "second-key"' in content
    assert 'api_key = "first-key"' not in content


def test_setup_handles_special_chars(temp_home):
    """setup escapes TOML special characters in user input."""
    with (
        mock.patch("builtins.input", side_effect=[
            'my "provider"',
            'model\\v1',
            'https://example.com/api',
        ]),
        mock.patch("haxjobs.interfaces.setup_cli.getpass", return_value='key\\with"quotes'),
    ):
        run_setup()

    content = haxjobs.config.PROVIDER_CONFIG_PATH.read_text()
    assert 'name = "my \\"provider\\""' in content
    assert 'model = "model\\\\v1"' in content
    assert 'api_key = "key\\\\with\\"quotes"' in content
