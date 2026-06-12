# Hermes Job Pipeline — Status Dashboard

## Overview
Real-time snapshot of the automated job discovery and application pipeline. 8 platforms scanning ~50 companies, with AI-powered fit scoring and pack generation.

## Learning Objectives
The viewer will understand:
1. Pipeline coverage — which platforms and how many companies are being scanned
2. Throughput — how many jobs are flowing through the system
3. Outcomes — which roles passed scoring, which are under review, and what was rejected

---

## Section 1: Sites Scanned

**Key Concept**: Multi-platform coverage across ATS APIs, job boards, and recruitment agency feeds.

**Content**:
- Lever API: 19 companies (Spotify, Monzo, Revolut, Cloudflare, Stripe, GitHub, Grafana, Palantir...)
- Ashby API: 14 companies (Notion, Vercel, Linear, Docker, Snowflake, Cohere, Plaid...)
- Greenhouse API: 16 companies (Wise, Intercom, Datadog, GitLab, Anthropic, DeepMind, HubSpot...)
- HN Who Is Hiring: monthly auto-discovery
- MongooseJobs: RSS feed
- Reed.co.uk, CWJobs, Experis, BCG: browser-based graylist

**Visual Element**:
- Type: platform icon grid with company counts
- Treatment: 8 platform cards with big count numbers

**Text Labels**:
- Headline: "8 PLATFORMS"
- Subhead: "~50 Companies Tracked"
- Platform labels: "Lever 19", "Ashby 14", "Greenhouse 16", "HN Monthly", "MongooseJobs", "Reed", "CWJobs", "Experis"

---

## Section 2: Jobs Extracted

**Key Concept**: Raw intake volume — every job that passed keyword and location filters.

**Content**:
- 52 total jobs extracted
- Sources: 36 from Spotify/Lever, 14 from MongooseJobs RSS, 2 manual
- 44 still pending processing
- Filter: Python, Backend, AI, Full Stack roles in London/UK only

**Visual Element**:
- Type: big KPI number + source breakdown bar
- Emphasis: "52" as largest number on the dashboard

**Text Labels**:
- Headline: "52 JOBS EXTRACTED"
- Sub-labels: "36 Lever API", "14 MongooseJobs", "2 Manual"
- Status: "44 Pending · 8 Processed"

---

## Section 3: Jobs Fitted

**Key Concept**: AI-scored packs with tailored CVs, cover letters, and Q&A.

**Content**:
- 7 scored packs generated
- Scoring: stack match + role match + experience + location bonus + entry-level boost
- 2 auto-apply (80+), 5 review (60-79), 0 rejected (<60)

**Visual Element**:
- Type: score distribution gauge or segmented bar
- Color coding: green 80+, amber 60-79, red <60

**Text Labels**:
- Headline: "7 PACKS GENERATED"
- Segments: "2 Auto-Apply", "5 Review", "0 Rejected"

---

## Section 4: Auto-Apply (Score 80+)

**Key Concept**: Strong matches — packs ready to submit.

**Content**:
- Senior Backend Engineer — Subscriptions @ Spotify — Score: 82
- Backend Engineer — Release @ Spotify — Score: 82

**Visual Element**:
- Type: green-highlighted cards with checkmark icons
- Treatment: bold role names, company logo area, score badge

**Text Labels**:
- Headline: "AUTO-APPLY"
- Card 1: "Senior Backend Engineer · Subscriptions · Spotify · 82"
- Card 2: "Backend Engineer · Release · Spotify · 82"

---

## Section 5: Review (Score 60-79)

**Key Concept**: Decent fits with notable gaps — worth a look but needs human judgment.

**Content**:
- Senior Full Stack Engineer — WhoSampled @ Spotify — 68
- Full Stack Engineer — Audiobooks @ Spotify — 67
- Gen AI Engineering Manager @ Metrica — 67
- Senior Full Stack Engineer — Audiobooks @ Spotify — 64
- Senior Fullstack Engineer — Commerce Platform @ Spotify — 62

**Visual Element**:
- Type: amber-highlighted list cards
- Treatment: role names, scores, brief gap notes

**Text Labels**:
- Headline: "REVIEW"
- Listed roles with scores

---

## Section 6: Rejected (Score <60)

**Key Concept**: Below threshold — not a fit.

**Content**:
- 0 rejected

**Visual Element**:
- Type: empty state indicator
- Treatment: "None" with a clean zero

**Text Labels**:
- Headline: "REJECTED"
- Value: "0"

---

## Data Points (Verbatim)

### Statistics
- "52 jobs extracted"
- "8 platforms active"
- "~50 companies tracked"
- "7 packs generated"
- "2 auto-apply (score 80+)"
- "5 review (score 60-79)"
- "0 rejected (score <60)"
- "44 pending intake files"

### Key Terms
- **Auto-Apply**: Score 80+. Strong match. Pack includes tailored CV, cover letter, Q&A.
- **Review**: Score 60-79. Decent fit with gaps. Needs human judgment before applying.
- **Rejected**: Score below 60. Not a fit.

---

## Design Instructions

### Style Preferences
- Bold, clean, professional
- Big numbers for KPIs
- Sharp visual hierarchy
- Minimalist — no clutter, no unnecessary decoration
- Dark accent elements for contrast

### Layout Preferences
- Dashboard grid with clear sections
- Metrics first (big numbers at top)
- Lists below with color-coded status

### Other Requirements
- Pipeline status infographic for personal dashboard use
- Landscape orientation preferred
- Readable at a glance
