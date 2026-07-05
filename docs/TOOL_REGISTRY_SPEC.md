# HaxJobs Tool Registry Specification

The tool registry is the product spine. Every HaxJobs capability — job discovery, fit evaluation, pack generation, decision recording — is exposed as a tool. The agent harness dispatches tools. The FastAPI app calls the same service functions. The React UI is a skin over the tools.

This document is the contract. Future plans must conform to it.

## Brain + Organs model

```
         ┌──────────────────────────────┐
         │      Agent Harness (Brain)    │
         │  LLM reasoning · tool dispatch│
         │  Prompt tiers · safety gates  │
         └──────┬───────┬───────┬────────┘
                │       │       │
        ┌───────┘  ┌────┘  ┌────┘
        ▼          ▼       ▼
   ┌─────────┐ ┌───────┐ ┌─────────┐
   │Discovery│ │Evaluate│ │Pack Gen │  ...
   │ Engine  │ │Engine  │ │ Engine  │
   └─────────┘ └───────┘ └─────────┘
```

Every organ is an independent Python module, registered as a tool, callable by the agent during `run_with_tools()`, and testable in isolation.

## Tool modes

Tools are grouped by workflow context. The agent sees only the tools relevant to its current task:

| Mode | Use | Tools |
|---|---|---|
| `profile` | onboarding / profile enrichment | profile_read, profile_write, profile_schema, profile_gaps |
| `discovery` | finding and promoting jobs | discover_jobs, profile_read, web_search, fetch_page |
| `evaluation` | scoring a known job | evaluate_fit, profile_read |
| `application` | pack generation | generate_pack, profile_read |
| `decision` | user feedback | record_decision |
| `admin` | local diagnostics only | db_query, profile_read, profile_schema |
| `outreach_future` | future contact/message draft work | find_contacts, draft_message |
| `learning_future` | future preference analysis | analyze_patterns |

## Product tools

### discover_jobs

**Status:** BUILD (plan 102)

Run ATS scrapers (Greenhouse, Ashby, Lever) and optional web search to find jobs matching the profile. Promotes new jobs to the `jobs` table. Auto-evaluates likely matches when `auto_evaluate=true`.

**Input:**

```json
{
  "sources": ["greenhouse", "ashby", "lever", "web"],
  "auto_evaluate": true
}
```

**Output (success):**

```json
{
  "ok": true,
  "found": 42,
  "new": 15,
  "promoted": 12,
  "evaluated": 10,
  "packed": 6,
  "errors": 1,
  "jobs": [
    {"id": 1, "title": "Backend Engineer", "company": "Acme", "url": "...", "location": "Remote", "source": "greenhouse"}
  ]
}
```

**Tables:** discovered_jobs (read), jobs (write), evaluations (write, if auto_evaluate), activity_log (write)

**Agent may call automatically:** yes

**Max output tokens:** 4000

---

### evaluate_fit

**Status:** BUILD (plan 102)

Score a job from the `jobs` table against the full profile. Calls the LLM internally with the evaluation prompt. Parses structured JSON with `extract_json()`. Writes result to `evaluations` table. Auto-generates pack for L1/L2 when `auto_generate_pack=true`.

**Input:**

```json
{
  "job_id": 42,
  "auto_generate_pack": true
}
```

**Output (success):**

```json
{
  "ok": true,
  "job_id": 42,
  "fit_score": 85,
  "level": 1,
  "level_name": "L1",
  "fit_verdict": "Excellent fit",
  "strongest_matches": ["5 years Python", "AWS experience"],
  "major_gaps": ["No Kubernetes"],
  "sponsorship_risk": "low",
  "summary": "Strong match for this backend role...",
  "pack": {"ok": true, "pack_dir": "packs/acme/backend_python", "files": [...]}
}
```

**Output (error):**

```json
{"ok": false, "code": "job_not_found", "error": "Job 42 not found"}
{"ok": false, "code": "profile_missing", "error": "No profile loaded"}
{"ok": false, "code": "invalid_agent_json", "error": "LLM returned unparseable output"}
```

**Tables:** jobs (read), evaluations (write), packs (indirect via generate_pack), activity_log (write)

**Agent may call automatically:** yes (evaluation is the agent's job)

**Max output tokens:** 2000

---

### generate_pack

**Status:** BUILD (plan 102)

Generate an application pack for an evaluated job. For L1/L2 only — L3/L4 require manual review unless `force=true`. Creates fit report, cover letter, field answers, and interview questions as markdown files under `packs/<company>/<variant>/`. References reusable CV variants — never generates per-job CVs.

**Input:**

```json
{
  "job_id": 42,
  "force": false
}
```

**Output (success):**

```json
{
  "ok": true,
  "job_id": 42,
  "pack_dir": "packs/acme/backend_python",
  "files": ["fit_report.md", "cover_letter.md", "field_answers.md", "interview_questions.md", "metadata.json"],
  "metadata": {"cv_variant": "backend_python", "pack_owns_cv": false}
}
```

**Output (error):**

```json
{"ok": false, "code": "job_not_found", "error": "Job 42 not found"}
{"ok": false, "code": "evaluation_required", "error": "Job must be evaluated before generating a pack"}
{"ok": false, "code": "manual_review_required", "error": "L3/L4 jobs require manual review"}
```

**Tables:** jobs (read, update pack_status), evaluations (read)

**Agent may call automatically:** yes (for L1/L2 after evaluation)

**Max output tokens:** 1500

---

### record_decision

**Status:** BUILD (plan 102)

Record a user decision on a job. Writes to the `decisions` table and updates the job status. Valid decisions: apply, maybe, save, skip, reject.

**Input:**

```json
{
  "job_id": 42,
  "decision": "apply",
  "reason": "Strong Python backend role, matches my experience"
}
```

**Output (success):**

```json
{
  "ok": true,
  "job_id": 42,
  "decision": "apply",
  "decision_id": 128
}
```

**Output (error):**

```json
{"ok": false, "code": "job_not_found", "error": "Job 42 not found"}
{"ok": false, "code": "invalid_decision", "error": "Decision must be apply, maybe, save, skip, or reject"}
```

**Tables:** decisions (write), jobs (update status), activity_log (write)

**Agent may call automatically:** yes, but only with user-specified decision

**Max output tokens:** 500

---

### find_contacts

**Status:** FUTURE

Search company pages and LinkedIn for hiring managers and team leads matching a role. Returns contacts with name, title, LinkedIn URL, and confidence score. Requires user approval before use.

**Input:**

```json
{
  "company": "Acme Corp",
  "role": "Engineering Manager"
}
```

**Output (success, future):**

```json
{
  "ok": true,
  "contacts": [
    {"name": "Jane Smith", "title": "VP Engineering", "linkedin_url": "...", "confidence": 0.85}
  ]
}
```

**Tables:** outreach_contacts (write, future)

**Agent may call automatically:** no — requires user approval

**Max output tokens:** 2000

---

### draft_message

**Status:** FUTURE

Template-fill a personalized outreach message using profile + job context. Returns subject line and message text. Never sends — requires user approval.

**Input:**

```json
{
  "contact_id": "abc123",
  "job_id": 42,
  "template": "default"
}
```

**Output (success, future):**

```json
{
  "ok": true,
  "subject_line": "Backend Engineer role at Acme",
  "message_text": "Hi Jane, I came across the Backend Engineer role...",
  "requires_approval": true
}
```

**Tables:** outreach_drafts (write, future)

**Agent may call automatically:** yes (drafts are safe, sending requires approval)

**Max output tokens:** 1500

---

### analyze_patterns

**Status:** FUTURE

Process the `decisions` table for trends. Returns preferred companies, preferred roles, salary trends, and profile tightening suggestions. This is the learning engine's data source.

**Input:**

```json
{
  "timeframe": "30d"
}
```

**Output (success, future):**

```json
{
  "ok": true,
  "preferred_companies": ["Acme", "TechCorp"],
  "preferred_roles": ["Backend Engineer", "Platform Engineer"],
  "salary_trend": {"median": 120000, "range": [90000, 150000]},
  "suggestions": ["Add Kubernetes to top skills", "Consider adding DevOps roles"]
}
```

**Tables:** decisions (read)

**Agent may call automatically:** yes (read-only analysis)

**Max output tokens:** 2000

---

## Support tools

### web_search

**Status:** DONE

Search the web via DuckDuckGo HTML. Returns compact result snippets with title and URL. Limited to 5 results. Available in discovery and admin modes only.

### fetch_page

**Status:** DONE

Fetch a public HTTP(S) page and return truncated visible text. SSRF-hardened: blocks localhost, private IPs, and validates redirect targets. Max 12,000 characters per page. Available in discovery mode only.

### db_query

**Status:** DONE

Run a read-only SELECT or WITH query against the HaxJobs SQLite database. Rejected operations: INSERT, UPDATE, DELETE, DDL, transactions, ATTACH, PRAGMA. Max 50 rows. Available in admin mode only — NOT a product workflow tool.

### profile_read

**Status:** DONE

Read the user's HaxJobs profile. Dot-path access for specific fields or full profile when no path given. Available in profile, discovery, evaluation, application, and admin modes.

### profile_write

**Status:** DONE

Write a value to a specific profile field using dot-path notation. Auto-parses JSON strings. Persists with 0600 permissions. Available in profile mode only.

### profile_schema

**Status:** DONE

Return the full HaxJobs profile JSON Schema. Available in profile and admin modes.

### profile_gaps

**Status:** DONE

Return a summary of profile gaps: required fields still empty, skills without evidence, roles without achievements, and detected employment gaps. Used by the onboarding agent to decide when to stop asking questions. Available in profile mode only.

---

## Safety rules

1. **All product tools return the same error shape:** `{"ok": false, "code": "machine_code", "error": "human readable message"}`
2. **All product tools return `ok: true` on success.**
3. **No tool sends applications or outreach messages without explicit user approval.**
4. **db_query is admin-only.** It must not appear in product workflow modes.
5. **profile_write is profile-mode only.** It must not be available during evaluation or discovery.
6. **find_contacts requires user approval before any real LinkedIn scraping.**
7. **generate_pack never creates per-job CVs.** Only references reusable CV variants.
8. **Tool output is capped per the max_output_tokens spec above.**
9. **Tools that write to the DB or profile must log to activity_log.**

## Output size rules

| Tool | Max output tokens |
|---|---|
| discover_jobs | 4000 |
| evaluate_fit | 2000 |
| generate_pack | 1500 |
| record_decision | 500 |
| find_contacts | 2000 |
| draft_message | 1500 |
| analyze_patterns | 2000 |
| web_search | 2000 |
| fetch_page | 4000 |
| db_query | 3000 |
| profile_read | 4000 |
| profile_write | 500 |
| profile_schema | 4000 |
| profile_gaps | 2000 |
