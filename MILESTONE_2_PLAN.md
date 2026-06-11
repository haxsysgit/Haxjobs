# Milestone 2: Site Discovery & Job Watching
## Archilles Job Pipeline — Next Phase

### What this milestone delivers

Archilles watches company career pages, recruitment firm sites, and tech company ATS boards. When new jobs matching Arinze's profile appear, they get queued for evaluation automatically.

### Architecture

```
Cron triggers (daily/weekly)
    │
    ├──→ Whitelist APIs (Lever, Ashby, Greenhouse) → company job boards
    │       │
    │       └──→ Extract jobs → filter by role/location → queue as pending intake
    │
    ├──→ Hacker News "Who Is Hiring" (monthly, 1st of month)
    │       │
    │       └──→ Parse comments → extract UK/London/Remote roles → queue
    │
    ├──→ Graylist scrapers (reed.co.uk, cwjobs.co.uk)
    │       │
    │       └──→ Discover companies → check if they use Tier 1 ATS → use API instead
    │
    └──→ Company discovery loop
            │
            └──→ Found a company → check Lever/Ashby/Greenhouse → subscribe to their board
```

### Site Strategy (from research report)

**WHITELIST — Use APIs, zero scraping needed:**
- Lever: `GET api.lever.co/v0/postings/{company}?mode=json`
- Ashby: `GET api.ashbyhq.com/posting-api/job-board/{company}`
- Greenhouse: Parse `boards.greenhouse.io/{company}` (clean HTML)
- HN Who Is Hiring: Firebase API `hacker-news.firebaseio.com/v0/item/{thread_id}.json`

**GRAYLIST — Playwright scraping with care:**
- reed.co.uk — discover companies, then use their ATS
- cwjobs.co.uk — same pattern
- cord.co — UK tech platform

**BLACKLIST — Do not touch:**
- LinkedIn, Indeed, Glassdoor, Otta

### Company target list (seed from Arinze's profile)

Initial companies to watch (from arinze_profile.local.json seed sites + UK tech companies using Lever/Ashby/Greenhouse):

Seed sites: experis.co.uk, bcg.com/careerhub, mongoosejobs.com

UK tech companies known to use Tier 1 ATS:
- Spotify (Lever — London office)
- GitLab (Greenhouse — remote UK)
- Datadog (Greenhouse — London)
- Monzo (Lever)
- Revolut (Lever)
- Wise (Greenhouse)
- GoCardless (Greenhouse)
- Deliveroo (Greenhouse)
- Intercom (Greenhouse — Dublin/London)
- Cloudflare (Lever — London)
- Notion (Ashby)
- Vercel (Ashby)
- Linear (Ashby)

### How it feeds into the pipeline

```
Discovery cron runs → finds new jobs → filters:
  1. Title contains: python, backend, engineer, developer, ai, automation
  2. Location contains: london, uk, remote uk, united kingdom, hybrid
  3. Not already queued (dedup by company+title)
→ Creates intake JSON with status:pending
→ Pipeline picks it up next run
→ Evaluates → generates pack if ≥60%
```

### Files to create on Archilles

```
/home/hermes/haxjobs/
├── discovery/
│   ├── lever_scraper.sh       # Query Lever API for company list
│   ├── ashby_scraper.sh       # Query Ashby API
│   ├── greenhouse_scraper.sh  # Parse Greenhouse boards
│   ├── hn_monthly.sh          # HN Who Is Hiring monthly
│   ├── reed_discovery.sh      # Reed company discovery
│   ├── companies.txt          # Curated company list
│   └── dedup.py               # Deduplication helper
└── cron/
    └── (new entries in crontab)
```

### Crontab schedule

```
0 8 * * *   /home/hermes/haxjobs/discovery/lever_scraper.sh      # Daily 8am
0 9 * * *   /home/hermes/haxjobs/discovery/ashby_scraper.sh      # Daily 9am
0 10 * * *  /home/hermes/haxjobs/discovery/greenhouse_scraper.sh  # Daily 10am
0 8 1 * *   /home/hermes/haxjobs/discovery/hn_monthly.sh         # 1st of month
0 12 */2 * * /home/hermes/haxjobs/discovery/reed_discovery.sh     # Every 2 days
```

### Important rules for Archilles

1. Rate limit: minimum 2-second delay between API calls
2. Rotate User-Agent headers (maintain a list of 5+ realistic UAs)
3. Respect robots.txt
4. Deduplicate: same company+title within 7 days = skip
5. Log all discovery runs to /home/hermes/haxjobs/state/discovery.log
6. Never scrape LinkedIn, Indeed, Glassdoor, or Otta
7. All output goes to intake/ as pending JSON files
8. The pipeline runner (every 3h) will pick them up
