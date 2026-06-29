"""Tests for the discovery scraper orchestrator."""

from __future__ import annotations


def test_run_all_scrapers_collects_results(monkeypatch) -> None:
    """The orchestrator collects all scraper results by source."""
    from discovery.scrapers import orchestrator

    monkeypatch.setattr(orchestrator, "scrape_greenhouse", lambda: {"datadog": {"found": 1, "new": 1, "errors": 0}})
    monkeypatch.setattr(orchestrator, "scrape_ashby", lambda: {"notion": {"found": 2, "new": 2, "errors": 0}})
    monkeypatch.setattr(orchestrator, "scrape_lever", lambda: {"spotify": {"found": 3, "new": 3, "errors": 0}})

    results = orchestrator.run_all_scrapers()

    assert results["greenhouse"]["datadog"]["found"] == 1
    assert results["ashby"]["notion"]["found"] == 2
    assert results["lever"]["spotify"]["found"] == 3


def test_run_all_scrapers_keeps_going_after_failure(monkeypatch) -> None:
    """One scraper failure does not stop the rest of discovery."""
    from discovery.scrapers import orchestrator

    def broken_scraper():
        raise RuntimeError("temporary source failure")

    monkeypatch.setattr(orchestrator, "scrape_greenhouse", broken_scraper)
    monkeypatch.setattr(orchestrator, "scrape_ashby", lambda: {"notion": {"found": 2, "new": 2, "errors": 0}})
    monkeypatch.setattr(orchestrator, "scrape_lever", lambda: {"spotify": {"found": 3, "new": 3, "errors": 0}})

    results = orchestrator.run_all_scrapers()

    assert results["greenhouse"]["error"] == "temporary source failure"
    assert results["ashby"]["notion"]["found"] == 2
    assert results["lever"]["spotify"]["found"] == 3
