# Application Workflow

## Goal

HaxJobs automates the mechanical parts of job applications so Arinze can focus on the parts that need human judgment.

## End-to-end pipeline

```
1. Scrapers discover jobs → raw job stored in discovered_jobs
2. Pre-discovery hooks run: dedup, blacklist, profile filter
3. Accepted jobs promote to jobs table
4. Classifier assigns role_family and cv_variant from haxjobs.toml profile
5. Evaluation agent scores fit (0-100), assigns level (L1-L4), identifies gaps
6. L1/L2: auto-fill role pack template → regenerate PDF/cover letter
7. L3/L4: no pack, flagged for report review
8. Cycle report generated: all evaluated jobs with links, scores, pack paths
9. Report saved to DB and delivered via configured channels
```

Manual job submissions (paste JD link) enter at step 1 — same normalization, same hooks, same pipeline.

## Evaluation levels and automation

| Level | Score | Automation |
|-------|-------|------------|
| L1 (Standard) | 75+ | Auto-pack: full template fill + PDF/cover letter |
| L2 (Quick Apply) | 50-74 | Auto-pack: template fill + cover letter |
| L3 (Lite) | 30-49 | Report only — appears in cycle report for manual review |
| L4 (Skip) | <30 | Report only — skip reason recorded |

## Pack generation

Packs are template-fill, not generated from scratch. Each role has a pre-built template in `application_templates/` with slots: `{company}`, `{hiring_manager_or_team}`, `{role_title}`, `{jd_match_points}`, `{company_reason}`, `{evidence_story}`, `{gap_note}`.

The agent fills slots with job-specific data. The filled HTML is regenerated into PDF/cover letter. No new CV per job — packs reference one of 7 reusable CV variants.

## Report output

Each pipeline cycle produces `reports/<cycle>.md`:

```
# HaxJobs Cycle Report — 2026-06-28

## Summary
- Discovered: 45 jobs
- Evaluated: 42 jobs
- L1 (auto-pack): 8
- L2 (auto-pack): 15
- L3 (manual review): 12
- L4 (skipped): 7

## L1/L2 — Packs Generated
| Job | Company | Score | Pack Path |
|-----|---------|-------|-----------|

## L3 — Manual Review Needed
| Job | Company | Score | Gap Summary |
|-----|---------|-------|-------------|

## L4 — Skipped
| Job | Company | Reason |
|-----|---------|--------|
```

## Safety boundaries

- **Never** auto-submit applications. Packs are preparation material only.
- **Never** auto-send outreach. Drafts may be generated; sending requires approval.
- **Never** fabricate experience. Template slots fill from real profile data. The gap-note system admits what's missing.
- **Never** generate per-job CVs. Seven reusable variants only.

## Future: 3-Agent Simulation Loop (v0.3)

After packs are generated, an optional coaching simulation stress-tests them against recruiter-style questioning. See ARCHITECTURE.md for details.
