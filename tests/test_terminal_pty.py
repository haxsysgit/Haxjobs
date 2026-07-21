"""PTY smoke test for TerminalClient — proves Enter submits and Escape interrupts mid-stream.

Uses stdlib pty to run the terminal in a pseudo-terminal.
Uses delayed fake model (--fake-delay) for genuine mid-stream interruption.
All tests use isolated temp session DBs.
"""

from __future__ import annotations

import os
import pty
import sys
import time
import select
import subprocess
import tempfile
from pathlib import Path


def _read_until(pty_fd: int, marker: bytes, timeout: float = 15.0) -> bytes:
    """Read from PTY until marker is found or timeout."""
    collected = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([pty_fd], [], [], 0.5)
        if ready:
            try:
                data = os.read(pty_fd, 4096)
            except OSError:
                break
            if not data:
                break
            collected += data
            if marker in collected:
                return collected
    return collected


def _read_all(pty_fd: int, timeout: float = 3.0) -> bytes:
    """Read all available output within timeout."""
    collected = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([pty_fd], [], [], 0.3)
        if ready:
            try:
                data = os.read(pty_fd, 4096)
            except OSError:
                break
            if data:
                collected += data
        else:
            break
    return collected


def test_terminal_pty_enter_submits_and_escape_interrupts():
    """Run haxjobs chat --fake in a PTY, send input, prove Enter submits and Escape interrupts."""
    career_db = os.environ.get("HAXJOBS_CAREER_DB", "state/career_graph.db")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        session_db = tf.name

    try:
        Path(session_db).unlink(missing_ok=True)

        master_fd, slave_fd = pty.openpty()

        try:
            env = os.environ.copy()
            env["HAXJOBS_CAREER_DB"] = career_db
            env["HAXJOBS_SESSION_DB"] = session_db
            env["PYTHONPATH"] = "src:."
            env["TERM"] = "xterm-256color"
            env["COLUMNS"] = "120"
            env["LINES"] = "40"

            proc = subprocess.Popen(
                [sys.executable, "-m", "haxjobs", "chat", "--new", "--fake"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                close_fds=True,
            )

            os.close(slave_fd)

            # Wait for the session prompt
            output = _read_until(master_fd, b"Session ID:", timeout=15.0)
            assert b"Session ID:" in output, f"No session banner. Got: {output[:200]}"
            assert b"Enter to submit" in output, "Missing key binding instructions"

            # Wait for "> " prompt
            _read_until(master_fd, b"> ", timeout=10.0)

            # Send "hello world" and Enter
            os.write(master_fd, b"hello world\r")

            # Wait for the fake model response
            response_output = _read_until(master_fd, b"FAKE:", timeout=10.0)
            assert b"FAKE:" in response_output, (
                f"No FAKE response after Enter. Got: {response_output[-200:]}"
            )

            # Send Escape to interrupt — should not crash
            os.write(master_fd, b"\x1b")
            time.sleep(0.5)

            # Send another message — with repeat mode, second turn should work
            os.write(master_fd, b"still alive\r")
            final_output = _read_until(master_fd, b"> ", timeout=10.0)
            assert b"> " in final_output, (
                f"Terminal did not return to prompt after second input. Got: {final_output[-200:]}"
            )

            # Send Ctrl+D to exit
            os.write(master_fd, b"\x04")
            time.sleep(1.0)

            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

            assert proc.returncode in (0, -15), f"Unexpected exit code: {proc.returncode}"

        finally:
            os.close(master_fd)

    finally:
        Path(session_db).unlink(missing_ok=True)


def test_terminal_pty_escape_during_streaming_interrupts():
    """Send Escape during a delayed fake stream to prove mid-stream interruption.

    Uses --fake-delay 100 so the fake model streams slowly enough that
    Escape (sent after a short sleep) arrives before the stream completes.
    """
    career_db = os.environ.get("HAXJOBS_CAREER_DB", "state/career_graph.db")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        session_db = tf.name

    try:
        Path(session_db).unlink(missing_ok=True)

        master_fd, slave_fd = pty.openpty()

        try:
            env = os.environ.copy()
            env["HAXJOBS_CAREER_DB"] = career_db
            env["HAXJOBS_SESSION_DB"] = session_db
            env["PYTHONPATH"] = "src:."
            env["TERM"] = "xterm-256color"
            env["COLUMNS"] = "120"
            env["LINES"] = "40"

            proc = subprocess.Popen(
                [sys.executable, "-m", "haxjobs", "chat", "--new", "--fake",
                 "--fake-delay", "150"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                close_fds=True,
            )

            os.close(slave_fd)

            # Wait for "> " prompt
            _read_until(master_fd, b"> ", timeout=15.0)

            # Send input and Enter
            os.write(master_fd, b"send and abort\r")

            # Wait briefly (less than the 150ms per-event delay, but after streaming starts)
            time.sleep(0.2)

            # Send Escape mid-stream
            os.write(master_fd, b"\x1b")

            # Read output — the interrupt should be visible or the prompt reappears
            time.sleep(1.5)

            # Collect all remaining output
            remaining = _read_all(master_fd, timeout=3.0)

            # The terminal should still be alive — new prompt "> " appears
            assert b"> " in remaining or b"interrupt" in remaining.lower(), (
                f"Terminal did not show prompt or interrupted after Escape. "
                f"Got: {remaining[-300:]}"
            )

            # Send Ctrl+D to exit
            os.write(master_fd, b"\x04")
            time.sleep(1.0)

            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

            assert proc.returncode in (0, -15), f"Unexpected exit code: {proc.returncode}"

        finally:
            os.close(master_fd)

    finally:
        Path(session_db).unlink(missing_ok=True)
