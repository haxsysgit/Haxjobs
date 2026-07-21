"""Source fetcher safety and event-loop responsiveness regressions."""

from __future__ import annotations

import asyncio
import threading

import pytest

from haxjobs.employment.job_source import JobSourceFetcher
from haxjobs.employment.schema import Job


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
async def test_blocking_resolver_times_out_without_blocking_event_loop():
    """A resolver that never returns cannot hold the event loop past its bound."""
    started = threading.Event()
    release = threading.Event()

    def blocking_resolver(hostname: str):
        started.set()
        release.wait(timeout=2)
        return [(2, "93.184.216.34")]

    fetcher = JobSourceFetcher(
        resolver=blocking_resolver,
        resolver_timeout=0.05,
    )
    job = {
        "external_ref": "resolver-timeout",
        "source_url": "https://example.com/jobs/timeout",
        "allowed_source_hosts": ["example.com"],
    }

    task = asyncio.create_task(fetcher.fetch_from_job(job))
    await asyncio.to_thread(started.wait)

    heartbeat = 0
    for _ in range(3):
        await asyncio.sleep(0.01)
        heartbeat += 1
    assert heartbeat == 3

    result = await task
    release.set()  # the timed-out to_thread worker is allowed to finish
    assert result.ok is False
    assert result.code == "dns_timeout"
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_shared_address_space_is_rejected_as_non_global():
    """DNS validation requires ipaddress.is_global, including 100.64/10."""
    fetcher = JobSourceFetcher(
        resolver=lambda hostname: [(2, "100.64.0.1")],
        transport_factory=lambda url, timeout: pytest.fail("transport must not run"),
    )
    result = await fetcher.fetch_from_job({
        "external_ref": "shared-address",
        "source_url": "https://example.com/jobs/shared",
        "allowed_source_hosts": ["example.com"],
    })

    assert result.ok is False
    assert result.code == "non_public_address"
    assert "100.64.0.1" in result.error


@pytest.mark.asyncio
async def test_nonnumeric_job_external_ref_source_inspection_succeeds():
    """Source diagnostics preserve a general string external_ref."""
    class Response:
        status = 200
        headers = {"Content-Type": "text/plain"}

        @staticmethod
        def read() -> bytes:
            return b"A source page"

    fetcher = JobSourceFetcher(
        resolver=lambda hostname: [(2, "93.184.216.34")],
        transport_factory=lambda url, timeout: Response(),
    )
    job = Job(
        job_id="job-vendor",
        external_ref="vendor-ref/alpha",
        title="Role",
        location="Remote",
        source_url="https://example.com/jobs/vendor",
        source_type="html",
        description="thin",
        observed_at="2026-07-21T00:00:00+00:00",
        allowed_source_hosts=["example.com"],
    )

    result = await fetcher.fetch_from_job(job)

    assert result.ok is True
    assert result.job_ref == "vendor-ref/alpha"
    assert result.visible_text == "A source page"


@pytest.mark.asyncio
async def test_transport_deadline_bounds_ignoring_transport():
    """The total source-fetch await times out even if transport ignores timeout."""
    started = threading.Event()
    release = threading.Event()

    fetcher = JobSourceFetcher(
        resolver=lambda hostname: [(2, "93.184.216.34")],
        transport_factory=lambda url, timeout: _BlockingResponse(started, release),
        fetch_timeout=0.05,
    )
    job = {
        "external_ref": "transport-timeout",
        "source_url": "https://example.com/jobs/timeout",
        "allowed_source_hosts": ["example.com"],
    }

    task = asyncio.create_task(fetcher.fetch_from_job(job))
    await asyncio.to_thread(started.wait)
    result = await task

    assert result.ok is False
    assert result.status == "unavailable"
    assert result.code == "fetch_timeout"
    assert result.error == "source fetch timed out"
    release.set()  # to_thread worker may finish after the safe timeout result


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
