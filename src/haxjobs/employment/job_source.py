"""Bounded saved-job source inspection — no arbitrary URLs, no browser, no search."""

from __future__ import annotations

import hashlib
import html.parser
import ipaddress
import json
import logging
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MAX_BYTES = 512 * 1024  # 512 KB
_MAX_VISIBLE_CHARS = 12_000
_TIMEOUT = 15.0
_USER_AGENT = "HaxJobs/1.0 (saved-job-source-inspection; +https://haxjobs.local)"

class SourceObservation(BaseModel):
    """Structured source retrieval observation — safe for model and JSONL."""

    ok: bool
    job_ref: str
    source_url: str
    final_url: str = ""
    source_type: str = ""
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = ""
    host: str = ""
    content_type: str = ""
    byte_length: int = 0
    visible_text: str = ""
    visible_text_length: int = 0
    content_hash: str = ""
    truncated_bytes: bool = False
    truncated_text: bool = False
    warnings: list[str] = Field(default_factory=list)
    code: str = ""
    error: str = ""


class _TextExtractor(html.parser.HTMLParser):
    """Extract visible text from HTML, stripping tags and scripts."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style", "noscript"):
            self._skip = False
        # Add newlines after block-level elements for readability
        if tag.lower() in ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)
                self._parts.append(" ")

    def get_text(self) -> str:
        return "".join(self._parts).strip()


def _validate_url(url_str: str) -> tuple[bool, str, str]:
    """Validate URL for HTTPS, no userinfo, no fragments, no non-default ports, no IP literals.

    Returns (ok, error, normalized_host).
    """
    try:
        parsed = urllib.parse.urlparse(url_str)
    except Exception:
        return False, "invalid URL", ""

    if parsed.scheme != "https":
        return False, f"non-HTTPS scheme: {parsed.scheme}", ""

    if parsed.username or parsed.password:
        return False, "URL contains userinfo", ""

    if parsed.fragment:
        return False, "URL contains fragment", ""

    hostname = parsed.hostname
    if not hostname:
        return False, "no hostname in URL", ""

    # Check if host is an IP literal (IPv4 or IPv6)
    try:
        ipaddress.ip_address(hostname)
        return False, f"IP-literal host not allowed: {hostname}", ""
    except ValueError:
        pass  # Not an IP literal, good

    # Check non-default port
    if parsed.port is not None and parsed.port != 443:
        return False, f"non-default port: {parsed.port}", ""

    return True, "", hostname.lower()


def _check_public_addresses(hostname: str, resolver: Callable | None = None) -> tuple[bool, str]:
    """Resolve hostname and check all addresses are public.

    In tests, pass a fake resolver that returns a list of (family, address) tuples.
    In production, uses socket.getaddrinfo.
    Returns (ok, error).
    """
    try:
        if resolver is not None:
            addrs = resolver(hostname)
        else:
            infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
            addrs = [(info[0], info[4][0]) for info in infos]
    except socket.gaierror as exc:
        return False, f"DNS resolution failed: {exc}"
    except Exception as exc:
        return False, f"address resolution failed: {exc}"

    if not addrs:
        return False, "no addresses resolved"

    for family, addr in addrs:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False, f"unparseable address: {addr}"

        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False, f"non-public address resolved: {addr} ({_ip_class(ip)})"

    return True, ""


def _ip_class(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    if ip.is_loopback:
        return "loopback"
    if ip.is_private:
        return "private"
    if ip.is_link_local:
        return "link_local"
    if ip.is_multicast:
        return "multicast"
    if ip.is_reserved:
        return "reserved"
    if ip.is_unspecified:
        return "unspecified"
    return "public"


def _extract_text(html_bytes: bytes, content_type: str) -> tuple[str, bool]:
    """Extract visible text from HTML or return plain text. Returns (text, is_html)."""
    is_html = "html" in content_type.lower()
    if is_html:
        # Try declared charset, fallback to utf-8
        text = html_bytes.decode("utf-8", errors="replace")
        parser = _TextExtractor()
        try:
            parser.feed(text)
        except Exception:
            pass  # Best-effort extraction
        return parser.get_text(), True
    else:
        text = html_bytes.decode("utf-8", errors="replace")
        return text, False


class JobSourceFetcher:
    """Retrieve and validate one source URL resolved from a saved Job.

    The model cannot supply arbitrary URLs. Runtime inspection accepts only the
    URL and host allowlist already persisted on the saved job.
    """

    def __init__(
        self,
        resolver: Callable | None = None,
        transport_factory: Callable | None = None,
        resolver_timeout: float = _TIMEOUT,
    ) -> None:
        """Resolver and transport_factory are for test injection only.

        resolver(hostname) -> [(family, address), ...]
        transport_factory(url, timeout) -> file-like response object
        resolver_timeout bounds the await of the off-loop resolver. Cancelling
        that await cannot stop an already-running resolver thread.
        """
        self._resolver = resolver
        self._transport_factory = transport_factory
        self._resolver_timeout = resolver_timeout

    async def _resolve_public_addresses(self, hostname: str) -> tuple[bool, str]:
        """Run resolver work off-loop with a bounded await."""
        import asyncio

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    _check_public_addresses, hostname, resolver=self._resolver
                ),
                timeout=self._resolver_timeout,
            )
        except asyncio.TimeoutError:
            return False, "DNS resolution timed out"

    async def fetch_from_job(self, job) -> SourceObservation:
        """Fetch source for a saved Job (Pydantic model or row dict).

        Resolves source_url and allowed_source_hosts from the Job.
        """
        # Support both Pydantic models and dict rows
        if hasattr(job, 'source_url'):
            source_url = job.source_url
            job_ref = str(job.external_ref or "")
            allowed_hosts = tuple(job.allowed_source_hosts) if hasattr(job, 'allowed_source_hosts') else ()
        else:
            source_url = job.get('source_url', '')
            job_ref = str(job.get('external_ref', '') or '')
            import json
            raw_hosts = job.get('allowed_source_hosts', '[]')
            if isinstance(raw_hosts, str):
                try:
                    allowed_hosts = tuple(json.loads(raw_hosts))
                except (json.JSONDecodeError, TypeError):
                    allowed_hosts = ()
            else:
                allowed_hosts = tuple(raw_hosts)

        # Validate URL
        url_ok, url_error, hostname = _validate_url(source_url)
        if not url_ok:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=source_url,
                status="invalid_source",
                code="url_validation_failed",
                error=url_error,
            )

        # Check allowed hosts
        allowed_lower = {h.lower() for h in allowed_hosts}
        if hostname not in allowed_lower:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=source_url,
                host=hostname,
                status="invalid_source",
                code="host_not_allowed",
                error=f"host {hostname} not in allowed_source_hosts",
            )

        # Check DNS addresses are all public
        ok, addr_error = await self._resolve_public_addresses(hostname)
        if not ok:
            timed_out = addr_error == "DNS resolution timed out"
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=source_url,
                host=hostname,
                status="unavailable" if timed_out else "invalid_source",
                code="dns_timeout" if timed_out else "non_public_address",
                error=addr_error,
            )

        # Fetch
        try:
            observation = await self._do_fetch_async(source_url, job_ref, hostname)
            return observation
        except Exception as exc:
            logger.warning("source fetch failed for %s: %s", source_url, exc)
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=source_url,
                host=hostname,
                status="unavailable",
                code="fetch_exception",
                error=f"fetch failed: {exc}",
            )

    async def _do_fetch_async(self, url: str, job_ref: str, hostname: str) -> SourceObservation:
        """Offload all blocking transport work, including injected fakes."""
        import asyncio

        return await asyncio.to_thread(self._do_fetch, url, job_ref, hostname)

    def _do_fetch(
        self, url: str, job_ref: str, hostname: str
    ) -> SourceObservation:
        """Internal fetch with byte/text limits and content type checks."""
        if self._transport_factory is not None:
            # Test transport injection
            result = self._transport_factory(url, _TIMEOUT)
            if isinstance(result, SourceObservation):
                return result
            # Otherwise assume it's a file-like response
            status_code = getattr(result, "status", 200)
            headers = getattr(result, "headers", {})
            body = getattr(result, "read", lambda: b"")()
            return self._process_response(
                url, job_ref, hostname, status_code, headers, body
            )

        # Real network fetch
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept-Encoding": "identity",
            },
        )

        # Disable ambient environment proxies
        proxy_handler = urllib.request.ProxyHandler({})
        # Disable redirects
        no_redirect_handler = _NoRedirectHandler()
        opener = urllib.request.build_opener(proxy_handler, no_redirect_handler)

        try:
            resp = opener.open(req, timeout=_TIMEOUT)
            status_code = resp.status
            headers = dict(resp.headers)
            body = resp.read(_MAX_BYTES + 1)  # +1 to detect overflow
        except urllib.error.HTTPError as exc:
            return self._process_response(
                url, job_ref, hostname, exc.code, dict(exc.headers), b""
            )
        except urllib.error.URLError as exc:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="unavailable",
                code="url_error",
                error=f"URL error: {exc.reason}",
            )
        except TimeoutError:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="unavailable",
                code="timeout",
                error="request timed out",
            )
        except Exception as exc:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="unavailable",
                code="fetch_error",
                error=f"fetch error: {exc}",
            )

        return self._process_response(url, job_ref, hostname, status_code, headers, body)

    def _process_response(
        self,
        url: str,
        job_ref: str,
        hostname: str,
        status_code: int,
        headers: dict,
        body: bytes,
    ) -> SourceObservation:
        """Map HTTP response to SourceObservation status."""
        content_type = headers.get("Content-Type", headers.get("content-type", ""))

        # Redirect
        if 300 <= status_code < 400:
            location = headers.get("Location", headers.get("location", ""))
            safe_target = ""
            if location:
                try:
                    parsed = urllib.parse.urlparse(location)
                    safe_target = parsed.hostname or location[:80]
                except Exception:
                    safe_target = location[:80]
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="redirected",
                code="redirect",
                error=f"HTTP {status_code}, target host: {safe_target}",
            )

        # Blocked
        if status_code in (401, 403):
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="blocked",
                code=f"http_{status_code}",
                error=f"source returned HTTP {status_code}",
            )

        # Rate limited
        if status_code == 429:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="rate_limited",
                code="http_429",
                error="source rate-limited the request",
            )

        # Gone
        if status_code in (404, 410):
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="gone",
                code=f"http_{status_code}",
                error=f"source returned HTTP {status_code}",
            )

        # Non-success
        if status_code < 200 or status_code >= 300:
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                status="unavailable",
                code=f"http_{status_code}",
                error=f"unexpected HTTP {status_code}",
            )

        # Success (2xx) — check content type
        if content_type and not _is_allowed_content_type(content_type):
            return SourceObservation(
                ok=False,
                job_ref=job_ref,
                source_url=url,
                host=hostname,
                content_type=content_type,
                status="invalid_source",
                code="unsupported_content_type",
                error=f"unsupported content type: {content_type}",
            )

        byte_length = len(body)
        truncated_bytes = byte_length > _MAX_BYTES
        if truncated_bytes:
            body = body[:_MAX_BYTES]

        # Hash content
        content_hash = hashlib.sha256(body).hexdigest()[:16]

        # Extract text
        visible_text, is_html = _extract_text(body, content_type)
        truncated_text = len(visible_text) > _MAX_VISIBLE_CHARS
        if truncated_text:
            visible_text = visible_text[:_MAX_VISIBLE_CHARS]

        warnings: list[str] = []
        if truncated_bytes:
            warnings.append(f"byte limit reached ({_MAX_BYTES}), content truncated")
        if truncated_text:
            warnings.append(f"text limit reached ({_MAX_VISIBLE_CHARS}), visible text truncated")
        if is_html and not visible_text.strip():
            warnings.append("HTML parsed but no visible text extracted")

        return SourceObservation(
            ok=True,
            job_ref=job_ref,
            source_url=url,
            final_url=url,
            source_type=content_type,
            status="current",
            host=hostname,
            content_type=content_type,
            byte_length=byte_length,
            visible_text=visible_text,
            visible_text_length=len(visible_text),
            content_hash=content_hash,
            truncated_bytes=truncated_bytes,
            truncated_text=truncated_text,
            warnings=warnings,
        )


def _is_allowed_content_type(content_type: str) -> bool:
    """Only allow textual content types (HTML, plain text)."""
    ct = content_type.lower().split(";")[0].strip()
    return ct in (
        "text/html",
        "text/plain",
        "application/xhtml+xml",
        "text/xml",
        "application/xml",
    )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Disable automatic redirect following."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

    http_error_301 = redirect_request
    http_error_302 = redirect_request
    http_error_303 = redirect_request
    http_error_307 = redirect_request
    http_error_308 = redirect_request
