"""CLI parser regressions."""

from __future__ import annotations

import pytest

from haxjobs.cli import main


@pytest.mark.parametrize(
    "argv",
    [
        ["chat", "--new", "--resume", "session-1"],
        ["chat", "--resume", "session-1", "--person-id", "person-1"],
        ["chat", "--track-id", "track-1"],
    ],
)
def test_chat_mode_and_scope_flags_are_rejected(argv: list[str]):
    """Resume/new are exclusive and scope flags require --new."""
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_migrate_requires_explicit_fixture_path():
    """Migration has no stale personal/default fixture fallback."""
    with pytest.raises(SystemExit) as exc:
        main(["migrate"])
    assert exc.value.code == 2
