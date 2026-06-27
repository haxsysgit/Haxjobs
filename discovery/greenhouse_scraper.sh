#!/bin/bash
# Greenhouse Board Scraper — parses Greenhouse job boards
# Greenhouse exposes boards at boards.greenhouse.io/{company} as clean HTML with JSON embed
set -euo pipefail

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")" && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---

BOARD_BASE="https://boards.greenhouse.io"
COMPANIES_FILE="$HAXJOBS_HOME/discovery/greenhouse_companies.txt"
INTAKE_DIR="$HAXJOBS_HOME/intake"
LOG_FILE="$HAXJOBS_HOME/state/discovery.log"
USER_AGENTS=(
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >> "$LOG_FILE"; }
random_ua() { echo "${USER_AGENTS[$((RANDOM % ${#USER_AGENTS[@]}))]}"; }

log "Greenhouse scraper starting..."

mkdir -p "$INTAKE_DIR"

while IFS= read -r company; do
    [[ -z "$company" || "$company" =~ ^# ]] && continue
    
    sleep $((2 + RANDOM % 3))
    
    url="${BOARD_BASE}/${company}"
    log "Querying: $url"
    
    html=$(curl -s -A "$(random_ua)" --max-time 30 "$url" 2>&1) || {
        log "ERROR: Failed to fetch $company"
        continue
    }
    
    # Greenhouse embeds jobs as JSON in a script tag
    echo "$html" | python3 -c "
import json, sys, re, subprocess

FILTER = '"$HAXJOBS_HOME/discovery/sharp_filter.py'
COMPANY = '$company'

html = sys.stdin.read()

# Find Greenhouse JSON embed: <script id=\"jobs-json\" ...>([...])</script>
match = re.search(r'<script[^>]*id=\"jobs-json\"[^>]*>(.*?)</script>', html, re.DOTALL)
if not match:
    # Try alternative pattern
    match = re.search(r'<script[^>]*type=\"application/json\"[^>]*id=\"jobs-json\"[^>]*>(.*?)</script>', html, re.DOTALL)

if not match:
    print('NO_JOBS_JSON')
    sys.exit(0)

try:
    jobs = json.loads(match.group(1))
except:
    print('PARSE_ERROR')
    sys.exit(0)

if not isinstance(jobs, list):
    jobs = [jobs]

queued = 0

for job in jobs:
    title = job.get('title', '')
    location = job.get('location', {}).get('name', '')
    dept = job.get('departments', [{}])[0].get('name', '') if job.get('departments') else ''
    desc = ''
    
    # Try to get description from metadata
    metadata = job.get('metadata', [])
    for m in metadata:
        if m.get('name') == 'Description' or m.get('name') == 'Job Description':
            desc = m.get('value', '') or m.get('content', '')
            break
    
    company_name = dept or COMPANY
    
    result = subprocess.run(
        ['python3', FILTER, 'save', company_name, title, desc[:5000], location, 'greenhouse_board', job.get('absolute_url', '')],
        capture_output=True, text=True, timeout=10
    )
    
    if result.stdout.startswith('SAVED='):
        queued += 1

print(f'QUEUED:{queued}')
" | while read line; do
        if [[ "$line" =~ ^QUEUED: ]]; then
            count="${line#QUEUED:}"
            log "  → Queued $count matching jobs from $company"
        elif [[ "$line" == "NO_JOBS_JSON" ]]; then
            log "SKIP: $company — no jobs JSON found"
        elif [[ "$line" == "PARSE_ERROR" ]]; then
            log "SKIP: $company — failed to parse jobs JSON"
        fi
    done
    
done < "$COMPANIES_FILE"

log "Greenhouse scraper complete"
