#!/bin/bash
# Hacker News "Who Is Hiring" — monthly scraper (runs on 1st of each month)
# Uses HN Firebase API to pull the thread, then parses comments for jobs
# Thread ID varies by month — auto-discovers the current month's thread
set -euo pipefail

# --- auto-detect HAXJOBS_HOME ---
if [ -z "${HAXJOBS_HOME:-}" ]; then
  HAXJOBS_HOME="$(cd "$(dirname "$0")" && pwd)"
fi
export HAXJOBS_HOME
# --- end auto-detect ---

HN_API="https://hacker-news.firebaseio.com/v0"
INTAKE_DIR="$HAXJOBS_HOME/intake"
LOG_FILE="$HAXJOBS_HOME/state/discovery.log"

log() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >> "$LOG_FILE"; }

MATCH_TERMS="python,backend,engineer,developer,ai,automation,fastapi,django,software,api"
LOCATION_TERMS="london,uk,remote uk,united kingdom,hybrid,england"

log "HN Who Is Hiring scraper starting..."

mkdir -p "$INTAKE_DIR"

# Get current month/year
MONTH=$(date +%B)
YEAR=$(date +%Y)
SEARCH_TERM="Ask HN: Who is hiring? (${MONTH} ${YEAR})"

log "Searching for: $SEARCH_TERM"

# Search HN Algolia API for the thread
SEARCH_URL="${HN_API}/../search?query=${SEARCH_TERM// /%20}&tags=story&hitsPerPage=5"
search_result=$(curl -s --max-time 15 "$SEARCH_URL" 2>/dev/null)

thread_id=$(echo "$search_result" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for hit in data.get('hits', []):
    title = hit.get('title', '')
    if 'who is hiring' in title.lower() and '${MONTH,,}' in title.lower():
        print(hit['objectID'])
        break
" 2>/dev/null)

if [[ -z "$thread_id" ]]; then
    log "Could not find HN Who Is Hiring thread for ${MONTH} ${YEAR}"
    exit 0
fi

log "Found thread: $thread_id"

# Fetch the thread item
thread_url="${HN_API}/item/${thread_id}.json"
thread_data=$(curl -s --max-time 30 "$thread_url" 2>/dev/null)

# Get comment IDs (kids)
echo "$thread_data" | python3 -c "
import json, sys, os
from datetime import datetime, timezone

INTAKE = '$INTAKE_DIR'
MATCH = '$MATCH_TERMS'.lower().split(',')
LOC = '$LOCATION_TERMS'.lower().split(',')
HN_API = '${HN_API}'
THREAD_ID = '$thread_id'

data = json.load(sys.stdin)
kids = data.get('kids', [])
print(f'TOTAL_COMMENTS:{len(kids)}')

# Fetch each comment
import urllib.request
queued = 0
skipped_irrelevant = 0

for kid_id in kids[:500]:  # Limit to first 500 to avoid excessive API calls
    try:
        url = f'{HN_API}/item/{kid_id}.json'
        req = urllib.request.Request(url, headers={'User-Agent': 'Hermes-Job-Discovery/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            comment = json.loads(resp.read())
    except:
        continue
    
    text = comment.get('text', '')
    if not text:
        continue
    
    text_lower = text.lower()
    
    # Must mention London/UK
    if not any(l in text_lower for l in LOC):
        skipped_irrelevant += 1
        continue
    
    # Must be a tech role
    if not any(t in text_lower for t in MATCH):
        continue
    
    # Extract first line as possible title
    lines = text.strip().split('\n')
    first_line = lines[0].strip()
    if len(first_line) > 120:
        first_line = first_line[:120] + '...'
    
    # Extract company from first line (usually formatted as 'Company Name | Role | Location')
    company = 'HN_Thread'
    parts = first_line.split('|')
    if len(parts) >= 1:
        company = parts[0].strip()
        # Strip HTML tags
        import re
        company = re.sub(r'<[^>]+>', '', company)
        if len(company) > 60:
            company = company[:60]
    
    ts = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    safe_company = company.replace(' ', '_').replace('/', '_')[:40]
    fname = f'{ts}_HN_{safe_company}.json'
    
    intake = {
        'received_at': datetime.now(timezone.utc).isoformat(),
        'source': 'hn_who_is_hiring',
        'source_url': f'https://news.ycombinator.com/item?id={THREAD_ID}#{kid_id}',
        'company': company,
        'title': first_line[:100],
        'jd_text': text[:2000],
        'location': 'See description',
        'status': 'pending'
    }
    
    path = os.path.join(INTAKE, fname)
    with open(path, 'w') as f:
        json.dump(intake, f, indent=2)
    queued += 1

print(f'QUEUED:{queued}')
print(f'SKIPPED_IRRELEVANT:{skipped_irrelevant}')
" 2>&1 | while read line; do
    if [[ "$line" =~ ^QUEUED: ]]; then
        count="${line#QUEUED:}"
        log "  → Queued $count matching HN jobs"
    elif [[ "$line" =~ ^TOTAL_COMMENTS: ]]; then
        count="${line#TOTAL_COMMENTS:}"
        log "Found $count comments in HN thread"
    elif [[ "$line" =~ ^SKIPPED_IRRELEVANT: ]]; then
        :
    fi
done

log "HN Who Is Hiring scraper complete"
