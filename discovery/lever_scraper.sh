#!/bin/bash
# Lever API Scraper — queries Lever job boards for companies in our target list
# Outputs: pending intake JSON files for matching jobs
set -euo pipefail

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")" && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---

API_BASE="https://api.lever.co/v0/postings"
COMPANIES_FILE="$HAXJOBS_HOME/discovery/companies.txt"
INTAKE_DIR="$HAXJOBS_HOME/intake"
LOG_FILE="$HAXJOBS_HOME/state/discovery.log"
USER_AGENTS=(
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >> "$LOG_FILE"; }
random_ua() { echo "${USER_AGENTS[$((RANDOM % ${#USER_AGENTS[@]}))]}"; }

log "Lever scraper starting..."

mkdir -p "$INTAKE_DIR"

while IFS= read -r company; do
    [[ -z "$company" || "$company" =~ ^# ]] && continue
    
    UA=$(random_ua)
    sleep $((2 + RANDOM % 3))  # 2-5 second delay
    
    url="${API_BASE}/${company}?mode=json"
    log "Querying: $url"
    
    response=$(curl -s -A "$UA" --max-time 30 "$url" 2>&1) || {
        log "ERROR: Failed to fetch $company"
        continue
    }
    
    # Check if valid JSON array (Lever returns [jobs] on success, {"ok":false,"error":"..."} on failure)
    job_count=$(echo "$response" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d) if isinstance(d, list) else -1)" 2>/dev/null)
    if [[ "$job_count" -lt 0 ]]; then
        log "SKIP: $company — not a valid Lever job list"
        continue
    fi
    
    log "Found $job_count jobs for $company"
    
    # Extract each job using sharp_filter WITH UK+Ireland location filtering
    echo "$response" | python3 -c "
import json, sys, subprocess, os, re

FILTER = '"$HAXJOBS_HOME/discovery/sharp_filter.py'
jobs = json.load(sys.stdin)
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
    title = job.get('text', '')
    desc = job.get('descriptionPlain', '') or job.get('description', '')
    location = job.get('categories', {}).get('location', '')
    company = job.get('categories', {}).get('team', 'Unknown')
    url = job.get('hostedUrl', '')
    
    # Skip if location is non-UK (strict filter)
    is_uk = location and any(p in location.lower() for p in UK_PATTERNS)
    if not is_uk:
        skipped_location += 1
        continue
    
    # Call sharp_filter to save (it handles dedup + title/seniority checks)
    result = subprocess.run(
        ['python3', FILTER, 'save', company, title, desc[:5000], location, 'lever_api', url],
        capture_output=True, text=True, timeout=10
    )
    
    if result.stdout.startswith('SAVED='):
        queued += 1
    elif result.stdout.startswith('SKIPPED'):
        pass  # Dedup or filter rejected

print(f'QUEUED:{queued}')
if skipped_location > 0:
    print(f'SKIPPED_LOCATION:{skipped_location}')
" 2>&1 | while read line; do
        if [[ "$line" =~ ^QUEUED: ]]; then
            count="${line#QUEUED:}"
            log "  → Queued $count matching jobs from $company"
        elif [[ "$line" =~ ^SKIPPED_LOCATION: ]]; then
            skipped="${line#SKIPPED_LOCATION:}"
            log "  → Skipped $skipped non-UK jobs from $company"
        fi
    done
    
done < "$COMPANIES_FILE"

log "Lever scraper complete"
