"""Shared pytest fixtures for HaxJobs tests.

Provides ``test_db`` — a per-test temporary SQLite database with the full schema,
isolated via ``monkeypatch`` on ``db.schema.DB_PATH``.

We monkeypatch ``db.schema.DB_PATH`` directly because ``haxjobs_config.DB_PATH``
is evaluated at import time and cannot be changed via ``setenv`` mid-session.

Usage::

    def test_something(test_db):
        from db.jobs import insert_job
        job_id = insert_job(title="...", ...)
"""
from __future__ import annotations

import pytest


@pytest.fixture
def test_db(tmp_path, monkeypatch) -> str:
    """Create a temp SQLite DB, patch db.schema.DB_PATH, init schema."""
    import db.schema as schema_mod
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(schema_mod, "DB_PATH", db_path)
    schema_mod.init()
    return db_path
