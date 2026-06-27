#!/bin/bash
# Ashby API Scraper — queries Ashby job boards for target companies
# Ashby API: GET api.ashbyhq.com/posting-api/job-board/{company}
# Returns: { jobs: [...], ... }
set -euo pipefail

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")" && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---

API_BASE="https://api.ashbyhq.com/posting-api/job-board"
COMPANIES_FILE="$HAXJOBS_HOME/discovery/ashby_companies.txt"
INTAKE_DIR="$HAXJOBS_HOME/intake"
LOG_FILE="$HAXJOBS_HOME/state/discovery.log"
USER_AGENTS=(
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >> "$LOG_FILE"; }
random_ua() { echo "${USER_AGENTS[$((RANDOM % ${#USER_AGENTS[@]}))]}"; }

log "Ashby scraper starting..."

mkdir -p "$INTAKE_DIR"

while IFS= read -r company; do
    [[ -z "$company" || "$company" =~ ^# ]] && continue
    
    sleep $((2 + RANDOM % 3))
    
    url="${API_BASE}/${company}"
    log "Querying: $url"
    
    response=$(curl -s -A "$(random_ua)" --max-time 30 "$url" 2>&1) || {
        log "ERROR: Failed to fetch $company"
        continue
    }
    
    # Validate JSON — Ashby returns {jobs:[], ...} on success
    is_valid=$(echo "$response" | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if isinstance(d,dict) and 'jobs' in d else 'bad')" 2>/dev/null)
    if [[ "$is_valid" != "ok" ]]; then
        log "SKIP: $company — invalid Ashby response"
        continue
    fi
    
    echo "$response" | python3 -c "
import json, sys, subprocess, re

FILTER = '"$HAXJOBS_HOME/discovery/sharp_filter.py'
data = json.load(sys.stdin)
jobs = data.get('jobs', [])
queued = 0
skipped_location = 0

# UK + Ireland location patterns
UK_PATTERNS = [
    'london', 'manchester', 'leeds', 'uk', 'united kingdom', 'england',
    'scotland', 'wales', 'ireland', 'remote uk', 'remote', 'hybrid uk',
    'birmingham', 'bristol', 'edinburgh', 'glasgow', 'cambridge', 'oxford',
    'reading', 'brighton', 'nottingham', 'sheffield', 'liverpool', 'newcastle',
    'cardiff', 'belfast', 'dublin', 'cork', 'galway', 'europe',
]

for job in jobs:
    title = job.get('title', '')
    location = job.get('location', '')
    desc = job.get('descriptionPlain', '') or job.get('description', '')
    apply_url = job.get('applyUrl', '')
    # Use the actual company name from the bash loop, not department
    company = '''$company'''
    
    # Skip if location is non-UK (strict filter)
    is_uk = location and any(p in location.lower() for p in UK_PATTERNS)
    if not is_uk:
        skipped_location += 1
        continue
    
    result = subprocess.run(
        ['python3', FILTER, 'save', company, title, desc[:5000], location, 'ashby_api', apply_url],
        capture_output=True, text=True, timeout=10
    )
    
    if result.stdout.startswith('SAVED='):
        queued += 1

print(f'QUEUED:{queued}')
if skipped_location > 0:
    print(f'SKIPPED_LOCATION:{skipped_location}')
" | while read line; do
        if [[ "$line" =~ ^QUEUED: ]]; then
            count="${line#QUEUED:}"
            log "  → Queued $count matching jobs from $company"
        elif [[ "$line" =~ ^SKIPPED_LOCATION: ]]; then
            skipped="${line#SKIPPED_LOCATION:}"
            log "  → Skipped $skipped non-UK jobs from $company"
        fi
    done
    
done < "$COMPANIES_FILE"

log "Ashby scraper complete"
