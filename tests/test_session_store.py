"""Session persistence tests — session creation, message replay, round-trip, permissions.

Plan 003 Phase 4: append-only session store with deterministic sequence order.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest

from haxjobs.agent_core.messages import (
    AssistantMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
)
from haxjobs.agent_core.session_store import SessionStore


@pytest.fixture
def store() -> SessionStore:
    return SessionStore(":memory:")


@pytest.fixture
def file_store() -> SessionStore:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = SessionStore(db_path)
    yield store
    store.close()
    try:
        os.unlink(db_path)
    except OSError:
        pass


# ── Session creation ──

def test_create_session(store: SessionStore):
    store.create_session("s1")
    session = store.get_session("s1")
    assert session is not None
    assert session["session_id"] == "s1"
    assert session["status"] == "active"
    assert session["turn_count"] == 0


def test_get_session_missing(store: SessionStore):
    assert store.get_session("nonexistent") is None


def test_latest_session_id(store: SessionStore):
    assert store.latest_session_id() is None
    store.create_session("s1")
    store.create_session("s2")
    assert store.latest_session_id() == "s2"


def test_latest_session_id_returns_none_when_empty(store: SessionStore):
    assert store.latest_session_id() is None


# ── Message append and load ──

def test_append_and_load_user_message(store: SessionStore):
    store.create_session("s1")
    msg = UserMessage(message_id="u1", turn_id="t1", content="hello")
    store.append_message("s1", msg)
    messages = store.load_messages("s1")
    assert len(messages) == 1
    assert messages[0]["payload_json"]["kind"] == "user"
    assert messages[0]["payload_json"]["content"] == "hello"


def test_append_and_load_assistant_message(store: SessionStore):
    store.create_session("s1")
    msg = AssistantMessage(
        message_id="a1", turn_id="t1", content="hi there", status="complete"
    )
    store.append_message("s1", msg)
    messages = store.load_messages("s1")
    assert len(messages) == 1
    assert messages[0]["payload_json"]["kind"] == "assistant"
    assert messages[0]["payload_json"]["status"] == "complete"


def test_append_and_load_tool_call_message(store: SessionStore):
    store.create_session("s1")
    msg = ToolCallMessage(
        message_id="tc1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="inspect_job_source",
        arguments='{"job_ref": "328"}',
    )
    store.append_message("s1", msg)
    messages = store.load_messages("s1")
    assert len(messages) == 1
    assert messages[0]["payload_json"]["kind"] == "tool_call"
    assert messages[0]["payload_json"]["call_id"] == "call_abc"


def test_append_and_load_tool_result_message(store: SessionStore):
    store.create_session("s1")
    msg = ToolResultMessage(
        message_id="tr1",
        turn_id="t1",
        call_id="call_abc",
        tool_name="inspect_job_source",
        ok=True,
        result={"status": "current"},
    )
    store.append_message("s1", msg)
    messages = store.load_messages("s1")
    assert len(messages) == 1
    assert messages[0]["payload_json"]["kind"] == "tool_result"
    assert messages[0]["payload_json"]["ok"] is True


def test_append_and_load_interrupted_assistant(store: SessionStore):
    store.create_session("s1")
    msg = AssistantMessage(
        message_id="a1",
        turn_id="t1",
        content="partial answer",
        status="interrupted",
    )
    store.append_message("s1", msg)
    messages = store.load_messages("s1")
    assert len(messages) == 1
    assert messages[0]["payload_json"]["status"] == "interrupted"
    assert messages[0]["payload_json"]["content"] == "partial answer"


# ── All message kinds round-trip ──

def test_all_message_kinds_round_trip(store: SessionStore):
    store.create_session("s1")
    msgs = [
        UserMessage(message_id="u1", turn_id="t1", content="first"),
        AssistantMessage(
            message_id="a1", turn_id="t1", content="response", status="complete"
        ),
        ToolCallMessage(
            message_id="tc1",
            turn_id="t1",
            call_id="c1",
            tool_name="t",
            arguments="{}",
        ),
        ToolResultMessage(
            message_id="tr1", turn_id="t1", call_id="c1", tool_name="t", ok=True, result={}
        ),
    ]
    for msg in msgs:
        store.append_message("s1", msg)

    loaded = store.load_messages("s1")
    assert len(loaded) == 4

    kinds = [m["payload_json"]["kind"] for m in loaded]
    assert kinds == ["user", "assistant", "tool_call", "tool_result"]


# ── Ordered message replay ──

def test_ordered_message_replay(store: SessionStore):
    store.create_session("s1")
    for i in range(10):
        store.append_message(
            "s1", UserMessage(message_id=f"u{i}", turn_id=f"t{i}", content=f"msg{i}")
        )
    messages = store.load_messages("s1")
    assert len(messages) == 10
    for i, m in enumerate(messages):
        assert m["payload_json"]["content"] == f"msg{i}"
        assert m["sequence"] == i + 1


# ── Mark turn settled ──

def test_mark_turn_settled(store: SessionStore):
    store.create_session("s1")
    store.mark_turn_settled("s1", 1)
    session = store.get_session("s1")
    assert session["turn_count"] == 1


# ── Mark session closed ──

def test_mark_session_closed(store: SessionStore):
    store.create_session("s1")
    store.mark_session_closed("s1")
    session = store.get_session("s1")
    assert session["status"] == "closed"


# ── File mode 0600 ──

def test_session_db_file_mode_0600(file_store: SessionStore):
    """Session database file has mode 0600."""
    db_path = file_store._conn.execute("PRAGMA database_list").fetchone()
    if db_path:
        real_path = db_path.get("file", "")
        if real_path and os.path.exists(real_path):
            file_mode = stat.S_IMODE(os.stat(real_path).st_mode)
            assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"


# ── Foreign key enforcement ──

def test_foreign_key_enforcement(store: SessionStore):
    """FK prevents orphan messages (session must exist before appending)."""
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute(
            "INSERT INTO session_messages (session_id, turn_id, message_kind, "
            "payload_json, created_at) VALUES ('nonexistent', 't1', 'user', '{}', '')"
        )


# ── WAL for file-backed DBs ──

def test_wal_enabled_for_file_backed_db(file_store: SessionStore):
    """WAL journal mode is enabled for file-backed databases."""
    row = file_store._conn.execute("PRAGMA journal_mode").fetchone()
    mode = row[0] if isinstance(row, (tuple, list)) else row["journal_mode"]
    assert mode.lower() == "wal"


# ── Empty messages load ──

def test_load_messages_empty(store: SessionStore):
    store.create_session("s1")
    messages = store.load_messages("s1")
    assert messages == []
