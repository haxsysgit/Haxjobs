# Archilles Job Pipeline — Implementation Plan

## Architecture Overview

```
YOU (anywhere)
  │
  ├─ Telegram ──→ Archilles (VPS) ──→ Evaluate ──→ Generate Pack ──→ Email you
  ├─ Email ────→                      │
  └─ Laptop ───→                      └──→ Telegram (questions/updates)
                                          └──→ Dashboard (Jade:9120)
```

Archilles is the engine. Jade is where we plan and where the dashboard lives.
All automation runs on Archilles. Nothing persistent runs on your laptop.

---

## Milestone 1: Full Pipeline (intake → evaluate → pack → email)

What you'll be able to do:
1. Paste a job link or JD into Telegram → Archilles picks it up
2. Forward a job email to archilleshaxsys@gmail.com → Archilles processes it  
3. Archilles evaluates fit against your profile, generates application pack
4. You get an email with: fit report, CV PDF, cover letter PDF, Q&A doc
5. If Archilles has questions, it asks on Telegram

### Components

#### 1. Intake Layer (on Archilles)

Two channels feed into a single queue:

**Telegram intake:**
- Archilles' Telegram gateway already runs in yolo mode
- New skill: when a message contains a URL or pasted JD → classify as job intake
- Extract: URL, raw JD text, source platform guess
- Queue as pending evaluation

**Email intake:**
- Archilles checks archilleshaxsys@gmail.com via IMAP (himalaya CLI)
- Cron job: every 15 minutes, scan inbox for forwarded job alerts
- Extract JD from email body/attachments
- Queue as pending evaluation

#### 2. Fit Evaluation (single agent)

For Milestone 1, one Hermes agent on Archilles:

```
Input: JD text + Arinze profile (Honcho memory + profile.json facts)

Output:
  - Fit score (0-100), weighted by:
      • Stack match (Python, FastAPI, SQLAlchemy, PostgreSQL, Docker): 40%
      • Role alignment (backend, AI, automation): 25%
      • Experience level match: 15%
      • Location/visa feasibility: 20%
  - Strongest matching evidence (specific profile facts)
  - Major gaps (e.g., "requires AWS production experience — not confirmed")
  - Sponsorship/visa risk flag
  - Recommendation: PURSUE / WEAK_FIT / SKIP
  - If questions exist for Arinze, include them for Telegram ping
```

Threshold: 60% or above → auto-generate pack. Below → archive with note.

#### 3. Pack Generation

Uses the existing `arinze-job-application-pack` skill (the one we just used):
- Tailored CV (PDF)
- Cover letter (PDF)
- Application Q&A + interview prep (Markdown)
- Saved to `/home/hermes/job-packs/{company}_{role}/`

#### 4. Notification Layer

**Email (primary):**
- Subject: "Job Fit Report: {role} at {company} ({score}%)"
- Body: fit summary, gaps, recommendation
- Attachments: CV PDF, cover letter PDF, Q&A doc

**Telegram (secondary — only for questions):**
- Only pings when Archilles needs clarification
- "Question about {role} at {company}: do you have production Kubernetes experience? This JD lists it as required."

#### 5. State Tracking

Stored in Hermes SQLite on Archilles:
```
job_id | company | role | source | status | fit_score | pack_path | created_at
```

Status flow: `intake → evaluating → evaluated → pack_ready → emailed | skipped`

---

## Site Discovery (cron-driven)

### Whitelist Sites (APIs, no scraping needed)

| Site | Method | Schedule |
|------|--------|----------|
| Lever API | `curl api.lever.co/v0/postings/{company}?mode=json` | Daily for curated company list |
| Ashby API | `curl api.ashbyhq.com/posting-api/job-board/{company}` | Daily |
| Greenhouse | HTML parse `boards.greenhouse.io/{company}` | Daily |
| HN Who Is Hiring | Algolia/Firebase API | Monthly (1st of month) |

### Graylist Sites (scraping, Playwright)

| Site | Method | Schedule |
|------|--------|----------|
| reed.co.uk | Playwright scrape Python+backend+london | Every 2 days |
| cwjobs.co.uk | Playwright scrape | Every 2 days |

### Company Discovery

For graylist sites: scrape listing → extract company name → check if they use Lever/Ashby/Greenhouse → if yes, use API instead for cleaner data.

### Blacklist (do not touch)

LinkedIn, Indeed, Glassdoor, Otta — not worth the legal risk, Cloudflare walls, or login requirements.

---

## The Forked Dashboard (future milestone)

Not the Hermes dashboard. A separate React+Vite app that LOOKS like the Hermes dashboard (same design language, theme, layout patterns) but talks to Archilles' job data.

### What it shows:
- Pipeline: all jobs and their statuses
- Job detail: JD, fit report, generated pack
- Activity feed: what Archilles did while you were away
- Profile: evidence library, gaps being tracked

### Where it runs:
- On Jade (your laptop), localhost:9120
- Reads from Archilles' SQLite via a lightweight API or direct SSH query

### What it does NOT include:
- Sessions, models, cron management, gateway config
- Any Hermes internal views
- Any columns or Kanban boards

### Build approach:
- Fork Hermes dashboard's React+Vite setup (same stack, same CSS patterns)
- Strip all views except what's needed
- Build job-specific views that read from Archilles data
- Deploy as a separate service on Jade

---

## Profile Evolution (future milestone)

As Archilles evaluates jobs and generates packs, it learns:
- Which gaps keep appearing (e.g., "no cloud evidence")
- Which claims get flagged as weak
- What kinds of roles consistently score highest

This feeds back into a growing profile that makes future matching tighter.

The 3-agent system (recruiter + applicant + ATS/judge) will accelerate this when we build it.

---

## Deployment Order

### NOW — Milestone 1
1. Set up intake channels on Archilles (Telegram handler + email IMAP cron)
2. Create fit evaluation skill for Archilles
3. Wire pack generation skill
4. Set up email notification via himalaya
5. Test end-to-end: paste link → get email with pack

### NEXT — Site Discovery
6. Deploy site scraping cron jobs (whitelist APIs first)
7. Add company discovery logic
8. Wire discovered jobs into the evaluation pipeline

### LATER — Dashboard
9. Fork Hermes dashboard UI
10. Build job-specific views
11. Connect to Archilles data

### FUTURE — 3-Agent + Profile
12. Build multi-agent evaluation pipeline
13. Profile evolution from agent criticism
14. Partial/full application automation for whitelisted sites

---

## File Structure on Archilles

```
/home/hermes/
├── job-pipeline/
│   ├── intake/
│   │   ├── telegram_handler.sh      # Telegram → intake queue
│   │   └── email_handler.sh         # IMAP scan → intake queue
│   ├── evaluate/
│   │   └── fit_evaluator.md         # Skill for single-agent evaluation
│   ├── generate/
│   │   └── (uses arinze-job-application-pack skill)
│   ├── notify/
│   │   └── email_report.sh          # Assemble + send email
│   ├── state/
│   │   └── pipeline.db              # SQLite tracking
│   ├── packs/                       # Generated application packs
│   └── cron/
│       ├── poll_email.sh            # Every 15 min
│       ├── discover_lever.sh        # Daily
│       ├── discover_reed.sh         # Every 2 days
│       └── hn_monthly.sh            # 1st of month
```
