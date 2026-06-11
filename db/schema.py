"""Database connection and schema initialization."""
import os
import sqlite3

DB_PATH = "/home/hermes/haxjobs/state/pipeline.db"


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
            status TEXT DEFAULT 'pending',
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
            evaluated_by TEXT DEFAULT 'hermes',
            evaluated_at TEXT NOT NULL DEFAULT (datetime('now')),
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
    """)
    conn.commit()
    conn.close()
