"""Job-search-native tools for the HaxJobs agent."""
from __future__ import annotations

import html
import ipaddress
import json as _json
import re
import socket
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from haxjobs.agent.registry import register
from haxjobs.db.schema import get_db

USER_AGENT = "HaxJobs/1.0 (+https://github.com/haxsysgit/Haxjobs)"
MAX_TEXT_CHARS = 12_000
MAX_SEARCH_RESULTS = 5
MAX_DB_ROWS = 50

PROFILE_PATH = Path.home() / ".haxjobs" / "profile.json"


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def _request_text(url: str, timeout: int = 10, max_bytes: int = 500_000) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as res:  # noqa: S310 - tool fetches user/model-supplied public URLs with scheme guard
        content_type = res.headers.get("content-type", "")
        charset = "utf-8"
        match = re.search(r"charset=([^;]+)", content_type, re.I)
        if match:
            charset = match.group(1).strip()
        return res.read(max_bytes).decode(charset, errors="replace")


def _html_to_text(page: str) -> str:
    page = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    page = html.unescape(page)
    return re.sub(r"\s+", " ", page).strip()


def web_search(query: str, max_results: int = MAX_SEARCH_RESULTS) -> dict[str, Any]:
    """Search the web via DuckDuckGo HTML and return compact result snippets."""
    if not query.strip():
        return {"error": "query is required"}
    max_results = max(1, min(int(max_results), MAX_SEARCH_RESULTS))
    url = "https://duckduckgo.com/html/?" + urlencode({"q": query})
    try:
        page = _request_text(url)
    except Exception as e:
        return {"error": f"web_search failed: {e}"}

    results = []
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.I | re.S,
    )
    for match in pattern.finditer(page):
        title = _html_to_text(match.group("title"))
        href = html.unescape(match.group("url"))
        if title and href:
            results.append({"title": title, "url": href})
        if len(results) >= max_results:
            break
    return {"query": query, "results": results}


def _public_http_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "url must start with http:// or https://"
    host = parsed.hostname
    if not host:
        return "url host is required"
    if host.lower() == "localhost":
        return "localhost URLs are not allowed"
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as e:
        return f"could not resolve host: {e}"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return "private/local URLs are not allowed"
    return None


def fetch_page(url: str) -> dict[str, Any]:
    """Fetch a public HTTP(S) page and return truncated visible text."""
    if err := _public_http_url(url):
        return {"error": err}
    try:
        page = _request_text(url)
    except Exception as e:
        return {"error": f"fetch_page failed: {e}"}
    text = _truncate(_html_to_text(page))
    return {"url": url, "text": text}


def _first_token(sql: str) -> str:
    cleaned = re.sub(r"(?s)/\*.*?\*/", " ", sql).strip()
    cleaned = re.sub(r"(?m)^\s*--.*$", " ", cleaned).strip()
    return (cleaned.split(None, 1)[0] if cleaned else "").lower()


def _readonly_authorizer(action, _arg1, _arg2, _db, _trigger):
    denied = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_PRAGMA,
    }
    return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK


def db_query(sql: str) -> dict[str, Any]:
    """Run a read-only SQLite query against the HaxJobs DB."""
    if _first_token(sql) not in {"select", "with"}:
        return {"error": "db_query only accepts SELECT or WITH queries"}

    conn = get_db()
    conn.set_authorizer(_readonly_authorizer)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_DB_ROWS + 1)
        truncated = len(rows) > MAX_DB_ROWS
        rows = rows[:MAX_DB_ROWS]
        return {
            "rows": [dict(row) for row in rows],
            "row_count": len(rows),
            "truncated": truncated,
        }
    except Exception as e:
        return {"error": f"db_query failed: {e}"}
    finally:
        conn.close()


register(
    "web_search",
    {
        "name": "web_search",
        "description": "Search the web for job listings or company career pages.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Maximum results, up to 5"},
            },
            "required": ["query"],
        },
    },
    web_search,
)
register(
    "fetch_page",
    {
        "name": "fetch_page",
        "description": "Fetch a public HTTP(S) page and return readable text.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "HTTP(S) URL to fetch"},
            },
            "required": ["url"],
        },
    },
    fetch_page,
)
register(
    "db_query",
    {
        "name": "db_query",
        "description": "Run a read-only SELECT/WITH query against the HaxJobs SQLite database.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "Read-only SQL query"},
            },
            "required": ["sql"],
        },
    },
    db_query,
)


# ── profile tools ──


def _load_profile() -> dict[str, Any] | None:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            return _json.load(f)
    return None


def _get_nested(data: dict, path: str) -> Any:
    parts = path.split(".")
    for p in parts:
        if isinstance(data, dict):
            data = data.get(p)
        elif isinstance(data, list) and p.isdigit():
            idx = int(p)
            data = data[idx] if 0 <= idx < len(data) else None
        else:
            return None
    return data


def _set_nested(data: dict, path: str, value: Any) -> dict:
    parts = path.split(".")
    target = data
    for p in parts[:-1]:
        if isinstance(target, dict):
            target = target.setdefault(p, {})
        elif isinstance(target, list) and p.isdigit():
            idx = int(p)
            while len(target) <= idx:
                target.append({})
            target = target[idx]
        else:
            return data
    if isinstance(target, dict):
        target[parts[-1]] = value
    return data


def profile_read(field_path: str | None = None) -> dict[str, Any]:
    """Read the user profile. If field_path is given, return only that dot-path field."""
    profile = _load_profile()
    if profile is None:
        return {"error": "No profile found. Complete onboarding first."}
    if field_path:
        value = _get_nested(profile, field_path)
        return {field_path: value}
    return {"profile": profile}


def profile_write(field_path: str, value: str) -> dict[str, Any]:
    """Write a value to a specific profile field using dot-path notation."""
    profile = _load_profile()
    if profile is None:
        return {"error": "No profile found. Complete onboarding first."}
    # Parse value — try JSON first, fall back to string
    try:
        parsed = _json.loads(value)
    except (_json.JSONDecodeError, TypeError):
        parsed = value
    profile = _set_nested(profile, field_path, parsed)
    profile["updated_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        _json.dump(profile, f, indent=2)
    PROFILE_PATH.chmod(0o600)
    return {"ok": True, "field": field_path}


# ponytail: read the schema file on each call so changes are live without restart
SCHEMA_CACHE_PATH = Path(__file__).resolve().parent.parent / "profile" / "profile_schema.json"


def profile_schema() -> dict[str, Any]:
    """Return the HaxJobs profile JSON Schema so the agent knows what fields exist."""
    if SCHEMA_CACHE_PATH.exists():
        with open(SCHEMA_CACHE_PATH) as f:
            return {"schema": _json.load(f)}
    return {"error": "Profile schema file not found"}


register(
    "profile_read",
    {
        "name": "profile_read",
        "description": (
            "Read the user's HaxJobs profile. Call without arguments for the full profile, "
            "or pass a dot-path like 'personal.email' or 'skills.languages' for a specific field. "
            "Use this before asking questions the profile already answers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field_path": {
                    "type": "string",
                    "description": "Dot-path to a field, e.g. 'personal.name' or 'work_experience'. Omit for full profile.",
                },
            },
            "required": [],
        },
    },
    profile_read,
)
register(
    "profile_write",
    {
        "name": "profile_write",
        "description": (
            "Write a value to the user's HaxJobs profile. Use dot-path notation to target a specific field. "
            "The value can be a plain string or a JSON string for arrays/objects. "
            "Examples: profile_write('personal.phone', '+447...') or "
            "profile_write('skills.ai_ml', '[{\"name\": \"PyTorch\", \"proficiency\": \"advanced\"}]'). "
            "ONLY write fields the user has explicitly confirmed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field_path": {"type": "string", "description": "Dot-path to the field to update"},
                "value": {"type": "string", "description": "Value to write (string or JSON-encoded)"},
            },
            "required": ["field_path", "value"],
        },
    },
    profile_write,
)
register(
    "profile_schema",
    {
        "name": "profile_schema",
        "description": (
            "Return the full HaxJobs profile JSON Schema — all fields, types, descriptions, and required flags. "
            "Call this when you need to know what fields exist in the profile before reading or writing."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    profile_schema,
)
