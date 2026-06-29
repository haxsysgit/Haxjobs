# Test State (2026-06-29)

18 test files, 207 tests (as of Plan 019 completion). All pass with `PYTHONPATH=. python3 -m pytest -q`.

## Active test files

| File | Coverage |
|------|----------|
| `test_discovery_ingestion.py` | Discovery dedup, blacklist, non-tech filter, promotion (Plan 015) |
| `test_role_family.py` | Config-driven role classification (Plan 017, rewritten from old JSON taxonomy) |
| `test_evaluator_agent_selection.py` | Pluggable agent selection via `select_agent()` (Plan 017) |
| `test_evaluator_parsing.py` | JSON extraction, validation, `EXPECTED_SCHEMA` (Plan 007) |
| `test_evaluation_writeback.py` | Decision defaults, skipped status, new Plan 018 fields |
| `test_auto_pack_levels.py` | L1/L2 auto-pack, template slot fill, all 7 role templates load (Plan 019) |
| `test_cycle_report.py` | Markdown report rendering, level separation, pack links (Plan 019) |
| `test_audit_regressions.py` | Regression guard for audit-found bugs |
| `test_pack_review_gate.py` | Pack approval state transitions |
| `test_outreach_review.py` | Outreach review flow |
| `test_pack_file_serving.py` | API pack file serving |
| `test_api_pagination.py` | /api/jobs pagination (Plan 013) |
| `test_db_batch_queries.py` | Batch job-list metadata queries (Plan 006) |
| `test_db_approval_gates.py` | Approval state transitions (Plan 004) |
| `test_import_intake_file.py` | Intake file import |
| `test_pack_directory.py` | Pack directory persistence |
| `test_api_auth.py` | API auth and CORS (Plan 002) |
| `conftest.py` | Shared `test_db` pytest fixture |

## Deleted during cleanup (not returning)

Files deleted during cleanup and intentionally not restored because their coverage was replaced by differently-scoped tests above:

- `test_role_family_db.py`, `test_role_family_backfill_api.py` — JSON taxonomy backfill, no longer applicable
- `test_evaluator_pack_prompt.py` — pack prompt tests, replaced by `test_auto_pack_levels.py`
- `test_generate_ready_packs.py`, `test_pack_builder_templates.py`, `test_pack_generator.py` — replaced by `test_auto_pack_levels.py`
- `test_manual_pack_generation.py`, `test_run_pipeline_pack_hook.py` — legacy manual-only gate tests, design changed to auto-pack for L1/L2
- `test_linkedin_import.py` — LinkedIn scraper deleted, discovery via manual submit + future scraper adapters
- `test_intake_evaluation_flow.py` — intake JSON split-brain path removed in Plan 014
