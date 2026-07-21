"""Source fetcher safety and event-loop responsiveness regressions."""

from __future__ import annotations

import asyncio
import threading

import pytest

from haxjobs.employment.job_source import JobSourceFetcher


class _BlockingResponse:
    status = 200
    headers = {"Content-Type": "text/plain"}

    def __init__(self, started: threading.Event, release: threading.Event) -> None:
        self._started = started
        self._release = release

    def read(self) -> bytes:
        self._started.set()
        self._release.wait(timeout=2)
        return b"Fetched off loop"


@pytest.mark.asyncio
async def test_blocking_transport_does_not_stop_event_loop():
    """Injected blocking transport runs in a thread while heartbeat ticks."""
    started = threading.Event()
    release = threading.Event()
    fetcher = JobSourceFetcher(
        resolver=lambda hostname: [(2, "93.184.216.34")],
        transport_factory=lambda url, timeout: _BlockingResponse(started, release),
    )
    job = {
        "external_ref": "328",
        "source_url": "https://example.com/jobs/328",
        "allowed_source_hosts": ["example.com"],
    }

    task = asyncio.create_task(fetcher.fetch_from_job(job))
    await asyncio.to_thread(started.wait)

    heartbeat = 0
    for _ in range(3):
        await asyncio.sleep(0.01)
        heartbeat += 1
    assert heartbeat == 3

    release.set()
    result = await task
    assert result.ok is True
    assert result.visible_text == "Fetched off loop"
