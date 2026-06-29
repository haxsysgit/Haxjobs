"""Database connection and schema initialization."""
import os
import sqlite3
from haxjobs_config import DB_PATH


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init():
    """Create all tables if they don't exist."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT DEFAULT '',
            jd_text TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            source TEXT DEFAULT 'unknown',
            source_quality TEXT DEFAULT 'unknown',
            status TEXT DEFAULT 'pending',
            role_family TEXT DEFAULT 'unknown',
            role_family_confidence REAL DEFAULT 0,
            recommended_cv_variant TEXT DEFAULT 'unknown',
            role_family_terms TEXT DEFAULT '[]',
            pack_status TEXT DEFAULT 'none',
            pack_dir TEXT DEFAULT '',
            outreach_status TEXT DEFAULT 'none',
            pack_review_status TEXT DEFAULT 'none',
            pack_review_notes TEXT DEFAULT '',
            pack_reviewed_at TEXT,
            classified_at TEXT,
            discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL UNIQUE,
            fit_score INTEGER NOT NULL,
            fit_verdict TEXT NOT NULL,
            level INTEGER NOT NULL,
            level_name TEXT NOT NULL,
            strongest_matches TEXT DEFAULT '[]',
            major_gaps TEXT DEFAULT '[]',
            sponsorship_risk TEXT DEFAULT 'medium',
            summary TEXT DEFAULT '',
            decision TEXT DEFAULT 'completed',
            skip_reason TEXT DEFAULT '',
            role_type TEXT DEFAULT '',
            evaluated_by TEXT DEFAULT '',
            evaluated_at TEXT NOT NULL DEFAULT (datetime('now')),
            agent TEXT DEFAULT '',
            profile_snapshot_json TEXT DEFAULT '{}',
            report_markdown TEXT DEFAULT '',
            pack_dir TEXT DEFAULT '',
            pack_template_id TEXT DEFAULT '',
            report_cycle_id TEXT DEFAULT '',
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL UNIQUE,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT DEFAULT '',
            decided_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS profile_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_json TEXT NOT NULL,
            captured_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            detail TEXT DEFAULT '',
            job_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            pattern_value TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            source_job_id INTEGER,
            match_count INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (source_job_id) REFERENCES jobs(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        CREATE INDEX IF NOT EXISTS idx_jobs_discovered ON jobs(discovered_at);
        CREATE INDEX IF NOT EXISTS idx_evaluations_score ON evaluations(fit_score);
        CREATE INDEX IF NOT EXISTS idx_evaluations_verdict ON evaluations(fit_verdict);
        CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at);
        CREATE INDEX IF NOT EXISTS idx_decisions_job ON decisions(job_id);
        CREATE INDEX IF NOT EXISTS idx_whitelist_active ON whitelist(active);
        CREATE INDEX IF NOT EXISTS idx_whitelist_type ON whitelist(pattern_type);

        -- Evaluation history (keeps old scores on re-evaluation)
        CREATE TABLE IF NOT EXISTS evaluation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            fit_score INTEGER NOT NULL,
            fit_verdict TEXT NOT NULL,
            level INTEGER NOT NULL,
            level_name TEXT NOT NULL,
            evaluated_by TEXT DEFAULT 'hermes',
            evaluated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_eval_history_job ON evaluation_history(job_id);

        -- Outreach contacts and drafts
        CREATE TABLE IF NOT EXISTS outreach_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            linkedin_url TEXT NOT NULL DEFAULT '',
            github_url TEXT DEFAULT '',
            found_via TEXT DEFAULT 'linkedin',
            relevance TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS outreach_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            contact_id INTEGER,
            subject TEXT NOT NULL DEFAULT '',
            message_text TEXT NOT NULL DEFAULT '',
            status TEXT DEFAULT 'draft',
            sent_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (contact_id) REFERENCES outreach_contacts(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_contacts_job ON outreach_contacts(job_id);
        CREATE INDEX IF NOT EXISTS idx_contacts_company ON outreach_contacts(company);
        CREATE INDEX IF NOT EXISTS idx_drafts_job ON outreach_drafts(job_id);
        CREATE INDEX IF NOT EXISTS idx_drafts_status ON outreach_drafts(status);

        -- Discovered / raw jobs (pre-promotion ingestion spine)
        CREATE TABLE IF NOT EXISTS discovered_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL DEFAULT 'manual',
            source_url TEXT DEFAULT '',
            apply_url TEXT DEFAULT '',
            ats TEXT DEFAULT '',
            external_id TEXT DEFAULT '',
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT DEFAULT '',
            jd_text TEXT DEFAULT '',
            raw_payload_json TEXT DEFAULT '{}',
            discovery_status TEXT NOT NULL DEFAULT 'new',
            filter_reason TEXT DEFAULT '',
            promoted_job_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (promoted_job_id) REFERENCES jobs(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_dj_source_url ON discovered_jobs(source_url);
        CREATE INDEX IF NOT EXISTS idx_dj_company ON discovered_jobs(company);
        CREATE INDEX IF NOT EXISTS idx_dj_title ON discovered_jobs(title);
        CREATE INDEX IF NOT EXISTS idx_dj_discovery_status ON discovered_jobs(discovery_status);
    """)
    _ensure_jobs_columns(conn)
    _ensure_jobs_indexes(conn)
    _ensure_evaluation_columns(conn)
    conn.commit()
    conn.close()


def _ensure_jobs_columns(conn):
    """Add reset-era job columns to older Archilles databases.

    SQLite cannot add multiple columns in one statement, so this keeps startup
    migrations tiny and safe. Each column is additive and has a default.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    required = {
        "source_quality": "TEXT DEFAULT 'unknown'",
        "role_family": "TEXT DEFAULT 'unknown'",
        "role_family_confidence": "REAL DEFAULT 0",
        "recommended_cv_variant": "TEXT DEFAULT 'unknown'",
        "role_family_terms": "TEXT DEFAULT '[]'",
        "pack_status": "TEXT DEFAULT 'none'",
        "pack_dir": "TEXT DEFAULT ''",
        "outreach_status": "TEXT DEFAULT 'none'",
        "pack_review_status": "TEXT DEFAULT 'none'",
        "pack_review_notes": "TEXT DEFAULT ''",
        "pack_reviewed_at": "TEXT",
        "classified_at": "TEXT",
    }
    for column, definition in required.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")


def _ensure_jobs_indexes(conn):
    """Create indexes that depend on reset-era job columns after migration."""
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_jobs_role_family ON jobs(role_family);
        CREATE INDEX IF NOT EXISTS idx_jobs_cv_variant ON jobs(recommended_cv_variant);
        CREATE INDEX IF NOT EXISTS idx_jobs_pack_status ON jobs(pack_status);
        CREATE INDEX IF NOT EXISTS idx_jobs_pack_review_status ON jobs(pack_review_status);
        CREATE INDEX IF NOT EXISTS idx_jobs_outreach_status ON jobs(outreach_status);
    """)


def _ensure_evaluation_columns(conn):
    """Add Plan 018 evaluation-outcome columns to older databases.

    Each column is additive with a safe default. SQLite requires one
    ALTER TABLE per column.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(evaluations)")}
    required = {
        "agent": "TEXT DEFAULT ''",
        "profile_snapshot_json": "TEXT DEFAULT '{}'",
        "report_markdown": "TEXT DEFAULT ''",
        "pack_dir": "TEXT DEFAULT ''",
        "pack_template_id": "TEXT DEFAULT ''",
        "report_cycle_id": "TEXT DEFAULT ''",
    }
    for column, definition in required.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE evaluations ADD COLUMN {column} {definition}")
