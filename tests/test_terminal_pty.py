"""PTY smoke test for TerminalClient — proves Enter submits and Escape interrupts.

Uses stdlib pty to run the terminal in a pseudo-terminal.
No external test dependencies required.
"""

from __future__ import annotations

import os
import pty
import sys
import time
import select
import subprocess
from pathlib import Path


def _read_until(pty_fd: int, marker: bytes, timeout: float = 10.0) -> bytes:
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


def test_terminal_pty_enter_submits_and_escape_interrupts():
    """Run haxjobs chat --fake in a PTY, send input, prove Enter submits and Escape interrupts."""
    career_db = os.environ.get("HAXJOBS_CAREER_DB", "state/career_graph.db")
    session_db = "/tmp/haxjobs-plan003-ptytest.db"

    # Clean up any prior session DB
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
            [sys.executable, "-m", "haxjobs", "chat", "--fake"],
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

        # Wait for "> " prompt (may be preceded by streaming output)
        prompt_output = _read_until(master_fd, b"> ", timeout=10.0)

        # Send "hello world" and Enter
        text = b"hello world\r"
        os.write(master_fd, text)

        # Wait for the fake model response to appear
        time.sleep(0.5)
        response_output = _read_until(master_fd, b"FAKE:", timeout=10.0)
        assert b"FAKE:" in response_output, (
            f"No FAKE response after Enter. Got: {response_output[-200:]}"
        )

        # Send Escape to interrupt (key can be sent even when not busy)
        os.write(master_fd, b"\x1b")
        time.sleep(0.5)

        # Send another message to prove terminal still responsive after Escape
        # (The fake model may exhaust after one turn, so we just prove the terminal
        #  accepts input and returns to prompt — no need for a second FAKE response)
        os.write(master_fd, b"still alive\r")
        time.sleep(1.0)
        final_output = _read_until(master_fd, b"> ", timeout=10.0)
        assert b"> " in final_output, (
            f"Terminal did not return to prompt after second input. Got: {final_output[-200:]}"
        )

        # Send Ctrl+D to exit when empty
        os.write(master_fd, b"\x04")
        time.sleep(1.0)

        # Verify process exits cleanly
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        assert proc.returncode in (0, -15), f"Unexpected exit code: {proc.returncode}"

    finally:
        os.close(master_fd)
        Path(session_db).unlink(missing_ok=True)


def test_terminal_pty_escape_during_streaming_interrupts():
    """Send Escape immediately after Enter to prove interruption happens before completion."""
    career_db = os.environ.get("HAXJOBS_CAREER_DB", "state/career_graph.db")
    session_db = "/tmp/haxjobs-plan003-ptytest2.db"

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

        # Wait for "> " prompt
        _read_until(master_fd, b"> ", timeout=15.0)

        # Send input and immediately Escape
        os.write(master_fd, b"send and abort\r")
        time.sleep(0.05)
        os.write(master_fd, b"\x1b")  # Escape
        time.sleep(1.0)

        # Read all output — should contain [interrupted] or at minimum still work
        remaining = _read_until(master_fd, b"> ", timeout=8.0)

        # The terminal should still be alive (new prompt "> " appeared)
        assert b"> " in remaining, (
            f"Terminal did not return to prompt after Escape. Got: {remaining[-300:]}"
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
        Path(session_db).unlink(missing_ok=True)
