"""Run configured discovery scrapers in sequence."""

from __future__ import annotations

from typing import Callable, TypeGuard, cast

from haxjobs.discovery.scrapers.ashby import scrape_ashby
from haxjobs.discovery.scrapers.greenhouse import scrape_greenhouse_companies, configured_greenhouse_companies
from haxjobs.discovery.scrapers.lever import scrape_lever

ScraperResult = dict[str, dict[str, int]]
ErrorResult = dict[str, str]
RunResult = ScraperResult | ErrorResult
ScraperRunner = Callable[[], ScraperResult]


def scrape_greenhouse() -> ScraperResult:
    """Run Greenhouse using configured board slugs."""
    return scrape_greenhouse_companies(configured_greenhouse_companies())


def is_error_result(result: RunResult) -> TypeGuard[ErrorResult]:
    """Return True when a scraper result is an error payload."""
    return "error" in result


def run_all_scrapers() -> dict[str, RunResult]:
    """Run every configured scraper without letting one failure stop the rest."""
    results: dict[str, RunResult] = {}
    scrapers: dict[str, ScraperRunner] = {
        "greenhouse": scrape_greenhouse,
        "ashby": scrape_ashby,
        "lever": scrape_lever,
    }

    for scraper_name, scraper_runner in scrapers.items():
        try:
            results[scraper_name] = scraper_runner()
        except Exception as exc:  # ponytail: scraper-level isolation for cron safety.
            results[scraper_name] = {"error": str(exc)}
            print(f"{scraper_name}: failed ({exc})")

    return results


def summarize_results(results: dict[str, RunResult]) -> None:
    """Print a compact summary for CLI runs."""
    for scraper_name, scraper_result in results.items():
        if is_error_result(scraper_result):
            print(f"{scraper_name}: error={scraper_result['error']}")
            continue

        company_results = cast(ScraperResult, scraper_result)
        found_count = 0
        matched_count = 0
        new_count = 0
        error_count = 0
        for company_result in company_results.values():
            found_count += int(company_result.get("found", 0))
            matched_count += int(company_result.get("matched", 0))
            new_count += int(company_result.get("new", 0))
            error_count += int(company_result.get("errors", 0))
        print(f"{scraper_name}: found={found_count}, matched={matched_count}, new={new_count}, errors={error_count}")


def main() -> int:
    """CLI entrypoint for all configured scrapers."""
    results = run_all_scrapers()
    summarize_results(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
