"""Tests for discover_jobs in product_tools."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_discover_unknown_source_returns_invalid_source(test_db):
    from haxjobs.product_tools import discover_jobs

    result = discover_jobs(sources=["nonexistent"])
    assert result["ok"] is False
    assert result["code"] == "invalid_source"


@patch("haxjobs.discovery.scrapers.ashby.scrape_ashby")
@patch("haxjobs.discovery.scrapers.lever.scrape_lever")
@patch("haxjobs.discovery.scrapers.orchestrator.scrape_greenhouse")
def test_discover_runs_all_scrapers_by_default(mock_greenhouse, mock_lever, mock_ashby, test_db):
    from haxjobs.product_tools import discover_jobs

    mock_greenhouse.return_value = {"found": 5, "new": 2, "errors": []}
    mock_lever.return_value = {"found": 3, "new": 1, "errors": []}
    mock_ashby.return_value = {"found": 2, "new": 0, "errors": []}

    result = discover_jobs(auto_evaluate=False)
    assert result["ok"] is True
    assert result["found"] == 10  # 5 + 3 + 2
    assert result["new"] == 3  # 2 + 1 + 0
    assert result["promoted"] >= 0


@patch("haxjobs.discovery.scrapers.orchestrator.scrape_greenhouse")
def test_discover_single_source(mock_greenhouse, test_db):
    from haxjobs.product_tools import discover_jobs

    mock_greenhouse.return_value = {"found": 4, "new": 1, "errors": []}

    result = discover_jobs(sources=["greenhouse"], auto_evaluate=False)
    assert result["ok"] is True
    assert result["found"] == 4
    assert result["new"] == 1


@patch("haxjobs.discovery.scrapers.orchestrator.scrape_greenhouse")
def test_discover_scraper_error_captured(mock_greenhouse, test_db):
    from haxjobs.product_tools import discover_jobs

    mock_greenhouse.side_effect = RuntimeError("Connection refused")

    result = discover_jobs(sources=["greenhouse"], auto_evaluate=False)
    # Scraper errors are captured, not fatal — result is still ok with errors logged
    assert result["ok"] is True
    assert len(result.get("errors", [])) >= 1
