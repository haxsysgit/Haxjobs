"""Tests for profile-aware discovery search helpers."""

from __future__ import annotations


def test_job_matches_profile_keeps_target_title() -> None:
    """Backend roles in preferred locations are worth scraping."""
    from discovery.profile_search import job_matches_profile

    assert job_matches_profile(
        "Backend Software Engineer",
        "London, UK",
        search_terms=["backend", "software engineer"],
        excluded_terms=["senior", "sales"],
        location_terms=["london", "uk", "remote"],
    )


def test_job_matches_profile_rejects_unrelated_title() -> None:
    """Discovery should not insert sales or random non-profile roles."""
    from discovery.profile_search import job_matches_profile

    assert not job_matches_profile(
        "Account Executive",
        "London, UK",
        search_terms=["backend", "software engineer"],
        excluded_terms=["account", "sales"],
        location_terms=["london", "uk", "remote"],
    )


def test_job_matches_profile_rejects_excluded_level() -> None:
    """Senior/staff/principal roles are filtered before insert."""
    from discovery.profile_search import job_matches_profile

    assert not job_matches_profile(
        "Senior Backend Engineer",
        "Remote UK",
        search_terms=["backend"],
        excluded_terms=["senior"],
        location_terms=["remote", "uk"],
    )
