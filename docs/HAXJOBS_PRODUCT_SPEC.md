# HaxJobs Product Spec

Status: reset spec
Date: 2026-06-11
Owner: Arinze
Agents: Jade builds locally, Archilles runs live automation and Telegram

## 1. One sentence

HaxJobs helps Arinze land interviews by keeping an accurate profile, discovering real source-first jobs, ranking them honestly, preparing reusable CV variants and per-job application material, and supporting LinkedIn networking with recruiters and hiring managers.

## 2. The real problem

Arinze is applying for jobs, but rejections can come from several places:

- weak fit for the role
- good fit but wrong CV angle
- applying through noisy third-party routes
- not reaching the right human at the company
- poor or generic form answers
- no follow-up or relationship with recruiters/hiring managers

HaxJobs exists to improve the whole job search loop, not just generate documents.

## 3. Product goals

### Goal 1: Build and maintain an accurate profile

The system must know Arinze truthfully:

- work history
- education
- projects
- skills
- visa/work authorization
- preferred roles
- location and relocation constraints
- salary expectations
- strongest proof points
- gaps and risk areas

The profile is evidence-based. The LLM can format and reason over it, but it must not invent facts.

### Goal 2: Discover jobs from the best sources

The system should find jobs from:

1. Company career pages and ATS pages
2. LinkedIn jobs, ideally with company apply links
3. Startup/company hiring pages
4. Trusted recruiters or agencies only when useful

Preference order:

```text
direct company source > LinkedIn company apply > LinkedIn Easy Apply > recruiter/agency board
```

The system should discover broadly across Arinze's role space, not only one title.

### Goal 3: Rank and explain fit

For each job, the system should produce:

- fit score
- role family
- recommended CV variant
- source quality
- visa/work authorization risk
- location risk
- application effort
- outreach opportunity
- why apply
- why skip or deprioritize

The ranking should be practical, not just keyword-based. A lower score job with a clear hiring manager contact may be more valuable than a higher score job through a noisy job board.

### Goal 4: Use a small CV variant library, not one CV per job

HaxJobs should maintain 5 to 7 reusable CV variants that cover Arinze's target role families.

Per-job CV generation is not the default.

The per-job pack should reference the correct CV variant and only generate the material that genuinely changes per job:

- cover letter
- fit report
- field-by-field application answers
- common application/interview Q&A
- Telegram summary

### Goal 5: Help Arinze network with real people

HaxJobs should help find and track:

- recruiters
- hiring managers
- engineering managers
- team leads
- founders at smaller companies
- relevant employees connected to the role

The system may draft messages, but should not send LinkedIn messages or connection requests without approval.

Long-term, outreach should become a lightweight CRM:

```text
found → drafted → approved → sent → replied → call booked → closed
```

### Goal 6: Automate applications where safe

Calling HaxJobs an automated application system is not wrong long term.

The correct approach is an automation ladder:

```text
Level 0: discovery and ranking only
Level 1: generate copy-paste answers and documents
Level 2: browser opens the form and pre-fills fields
Level 3: browser uploads CV and cover letter, then stops before submit
Level 4: one-click approved submit for known safe forms
Level 5: full automation for repeatable, trusted flows only
```

Today, HaxJobs should focus on Levels 0 to 2, with Level 3 for tested ATS platforms. Levels 4 and 5 are future work and must require explicit approval rules.

## 4. Non-goals for the reset phase

The reset phase should not try to:

- auto-apply everywhere
- generate a fresh CV for every job
- treat dashboards as the main product
- build a huge autonomous agent system before the workflow is stable
- send LinkedIn messages automatically
- rely on email as the main notification channel
- keep multiple competing sources of truth

## 5. Target role families

HaxJobs should discover many title variations, then map them into a smaller set of role families.

Example title universe:

- Junior Software Engineer
- Software Developer
- Software Engineer
- Python Developer
- Backend Developer
- Backend Engineer
- Full Stack Developer
- Full Stack Engineer
- AI Engineer
- Junior AI Engineer
- LLM Engineer
- Agent Designer
- AI Tooling Developer
- Automation Engineer
- Data Mining Python Developer
- Data Engineer, junior/backend leaning
- Platform Backend Engineer
- DevOps-leaning Backend Engineer

Initial CV variant families:

1. `backend_python`
   - Python Developer
   - Backend Developer
   - Backend Engineer
   - FastAPI Developer

2. `fullstack_python_react`
   - Full Stack Developer
   - Full Stack Engineer
   - Python React Developer

3. `ai_engineer_llm`
   - AI Engineer
   - Junior AI Engineer
   - LLM Engineer
   - Applied AI Engineer

4. `ai_automation_agents`
   - AI Tooling Developer
   - Automation Engineer
   - Agent Designer
   - Workflow Automation Developer

5. `junior_software`
   - Junior Software Engineer
   - Graduate Software Engineer
   - Software Developer
   - Entry-level SWE

6. `data_python`
   - Python Data Developer
   - Data Mining Developer
   - Analytics Engineer, Python leaning

7. `platform_backend`
   - Platform Engineer, backend leaning
   - Backend Infrastructure Engineer
   - Cloud Backend Developer

## 6. Application pack model

Each job can have a pack, but the pack should not generate a fresh CV by default.

A job pack should contain:

```text
packs/<job_id>/
  fit_report.md
  cover_letter.md
  field_answers.md
  interview_questions.md
  telegram_summary.md
  metadata.json
```

`metadata.json` should include:

```json
{
  "job_id": "...",
  "role_family": "backend_python",
  "recommended_cv_variant": "backend_python",
  "cv_file": "cv_variants/Arinze_Elenasulu_Backend_Python_CV.pdf",
  "application_url": "...",
  "source_quality": "direct_company",
  "fit_score": 82,
  "pack_status": "ready_for_review"
}
```

Optional generated PDFs can exist, but Markdown should be the editable source.

## 7. Discovery model

Discovery should normalize every job into one shape:

```json
{
  "title": "Python Developer",
  "company": "ExampleCo",
  "location": "London",
  "work_mode": "hybrid",
  "source": "linkedin",
  "source_quality": "linkedin_company_apply",
  "source_url": "https://linkedin.com/jobs/...",
  "apply_url": "https://company.com/careers/...",
  "description": "...",
  "discovered_at": "...",
  "raw": {}
}
```

Direct company apply URLs are preferred. LinkedIn-only URLs are still useful if they help discover the job or people.

## 8. Notification model

Only Archilles sends Telegram messages.

Telegram should be the primary control surface for Arinze.

Message types:

1. Daily discovery digest
2. High-fit urgent job
3. Pack ready
4. Outreach opportunity
5. System health issue

A good Telegram job message should include:

```text
Role and company
Fit score
Recommended CV variant
Apply link
Why it fits
Main gaps
Copy-paste field answers
Suggested outreach person/action
```

It should be short enough to read on a phone.

## 9. LinkedIn model

LinkedIn is used for:

- job discovery
- company research
- recruiter discovery
- hiring manager discovery
- profile context for outreach drafts

LinkedIn should not be used for unsafe bulk actions.

Rules:

- no auto-connect without approval
- no auto-message without approval
- low search volume
- session-cookie based browser access
- save useful people to an outreach queue
- draft messages in a human voice

## 10. Source of truth

The reset should move toward:

```text
SQLite database = source of truth for jobs, evaluations, packs, outreach
profile JSON = source of truth for Arinze facts
cv_variants/ = source of truth for stable CV files
packs/ = generated per-job artifacts
Telegram = delivery channel
Dashboard = optional review UI
```

Avoid having both `haxjobs.db` and `intake/*.json` act as competing databases.

## 11. Success criteria

HaxJobs is working when it can:

1. Discover 30 to 80 relevant jobs per week from good sources.
2. Group them into role families.
3. Recommend one of 5 to 7 CV variants for each job.
4. Rank jobs with useful reasoning.
5. Send a clear Telegram digest with links and next actions.
6. Generate per-job cover letters, fit reports, field answers, and interview Q&A on demand.
7. Find real LinkedIn people to contact for high-value roles.
8. Track outreach status and help book calls.
9. Keep browser automation safe and approval-based.

## 12. Product principle

HaxJobs is not just a document generator.

It is a job-search operating system for Arinze:

```text
profile truth → source-first discovery → fit ranking → reusable CV choice → per-job prep → outreach → interview pipeline
```
