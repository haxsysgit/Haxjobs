"""Web search and page fetch tools for the HaxJobs agent."""
from __future__ import annotations

import html
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from haxjobs.agent.registry import register

USER_AGENT = "HaxJobs/1.0 (+https://github.com/haxsysgit/Haxjobs)"
MAX_TEXT_CHARS = 12_000
MAX_SEARCH_RESULTS = 5


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


class _PublicRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if err := _public_http_url(newurl):
            raise ValueError(f"blocked unsafe redirect: {err}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_text(url: str, timeout: int = 10, max_bytes: int = 500_000) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    opener = build_opener(_PublicRedirectHandler)
    with opener.open(req, timeout=timeout) as res:  # noqa: S310 - URL is checked before fetch and on redirects
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
