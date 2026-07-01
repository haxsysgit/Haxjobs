"""HaxJobs database layer — single source of truth.

Re-exports all functions from db/ submodules. Import as
`import pipeline_db as db` from the project root.
"""
from .schema import DB_PATH, get_db, init
from .jobs import (
    insert_job, get_pending_jobs, get_job, get_all_jobs,
    update_job_status, job_count_by_status,
)
from .evaluations import (
    save_evaluation, get_evaluation, get_jobs_with_evaluations,
)
from .decisions import record_decision, get_decisions
from .activity import get_recent_activity
from .stats import get_stats
from .whitelist import (
    add_whitelist, remove_whitelist, get_whitelist,
    get_whitelist_for_eval, suggest_whitelist,
)
from .seed import seed_from_intake
from .discovered_jobs import (
    insert_discovered_job, find_duplicate, list_discovered_jobs,
    get_discovered_job, update_discovery_status, promote_discovered_job,
)
from .role_classification import (
    classify_job_payload, classify_existing_jobs, update_job_role_classification,
    infer_source_quality,
)
