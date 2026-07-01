"""Tests for decisions CRUD — the replacement for deleted favorites/saved_jobs tables."""
import pytest


class TestRecordDecision:
    def test_insert_and_retrieve(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_decisions

        job_id = insert_job(title="Test Job", company="TestCo", source="test")
        record_decision(job_id, "apply", "good fit, L1 role")
        decisions = get_decisions(job_id)

        assert len(decisions) == 1
        d = decisions[0]
        assert d["job_id"] == job_id
        assert d["decision"] == "apply"
        assert d["reason"] == "good fit, L1 role"
        assert d["decided_at"] is not None

    def test_multiple_decisions_ordered_newest_first(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_decisions

        job_id = insert_job(title="Multi", company="TestCo", source="test")
        record_decision(job_id, "skip", "first pass")
        record_decision(job_id, "apply", "reconsidered")
        decisions = get_decisions(job_id)

        assert len(decisions) == 2
        assert decisions[0]["decision"] == "apply"   # newest first
        assert decisions[1]["decision"] == "skip"

    def test_empty_for_no_decisions(self, test_db):
        from db.decisions import get_decisions

        result = get_decisions(999)
        assert result == []

    def test_only_returns_decisions_for_that_job(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_decisions

        job_a = insert_job(title="A", company="CoA", source="test")
        job_b = insert_job(title="B", company="CoB", source="test")

        record_decision(job_a, "apply", "")
        record_decision(job_b, "skip", "")

        assert len(get_decisions(job_a)) == 1
        assert len(get_decisions(job_b)) == 1
        assert get_decisions(job_a)[0]["decision"] == "apply"
        assert get_decisions(job_b)[0]["decision"] == "skip"


class TestAutoApplyStates:
    def test_returns_true_for_latest_auto_apply(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_latest_auto_apply_states

        job_id = insert_job(title="T", company="C", source="test")
        record_decision(job_id, "auto_apply")
        states = get_latest_auto_apply_states([job_id])

        assert states == {job_id: True}

    def test_returns_false_for_auto_apply_remove(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_latest_auto_apply_states

        job_id = insert_job(title="T", company="C", source="test")
        record_decision(job_id, "auto_apply")
        record_decision(job_id, "auto_apply_remove")
        states = get_latest_auto_apply_states([job_id])

        assert states == {job_id: False}

    def test_omits_job_with_no_auto_apply_decisions(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_latest_auto_apply_states

        job_a = insert_job(title="A", company="CA", source="test")
        job_b = insert_job(title="B", company="CB", source="test")

        record_decision(job_a, "apply", "manual")
        record_decision(job_b, "auto_apply")
        states = get_latest_auto_apply_states([job_a, job_b])

        assert job_a not in states  # only "apply", not auto_apply
        assert states[job_b] is True

    def test_ignores_non_auto_apply_decisions(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision, get_latest_auto_apply_states

        job_id = insert_job(title="T", company="C", source="test")
        record_decision(job_id, "skip")
        record_decision(job_id, "apply")
        states = get_latest_auto_apply_states([job_id])

        assert states == {}

    def test_empty_input_returns_empty(self):
        from db.decisions import get_latest_auto_apply_states

        assert get_latest_auto_apply_states([]) == {}


class TestActivityLogging:
    def test_record_decision_logs_activity(self, test_db):
        from db.jobs import insert_job
        from db.decisions import record_decision
        from db.activity import get_recent_activity

        job_id = insert_job(title="Logged", company="TestCo", source="test")
        record_decision(job_id, "apply", "strong match, L1")

        activity = get_recent_activity(limit=50)
        assert len(activity) >= 1
        # The most recent activity entry should be our decision
        decisions_events = [a for a in activity if a["event_type"] == "user_decision"]
        assert len(decisions_events) >= 1
        last = decisions_events[-1]
        assert "apply" in last["message"]
        assert "strong match" in last["message"]
