"""
Search-provider abstraction (section 26 of the spec). Default provider is
DuckDuckGo, which needs no API key. Adding a new provider means adding one
function and registering it in PROVIDERS -- nothing else in the app
depends on which provider is active.
"""
import ipaddress
import socket
import re
import time
import hashlib
import urllib.robotparser as robotparser
from urllib.parse import urlparse, unquote
from typing import Optional
import httpx
from bs4 import BeautifulSoup
import trafilatura
from .config import settings
from . import db

# --- trust tiers (section 5) --------------------------------------------
TIER_A_HINTS = (".gov", ".edu", "w3.org", "ietf.org", "iso.org", "nist.gov",
                "who.int", "un.org", "arxiv.org", "docs.python.org", "developer.mozilla.org")
TIER_B_HINTS = ("wikipedia.org", "owasp.org", "ieee.org", "acm.org", "readthedocs.io")
TIER_D_HINTS = ("reddit.com", "quora.com", "forum", "answers.")

class SearchError(Exception):
    """Raised when a search provider fails or returns nothing, so callers can tell
    the user honestly instead of silently answering as if nothing was searched."""

def classify_source(url: str) -> tuple[str, str]:
    host = urlparse(url).netloc.lower()
    if any(h in host for h in TIER_A_HINTS):
        return "A", "official/standards/education"
    if any(h in host for h in TIER_B_HINTS):
        return "B", "established technical organization"
    if any(h in host for h in TIER_D_HINTS):
        return "D", "forum/user-generated"
    return "C", "general web/blog"

def _robots_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(settings.user_agent, url)
    except Exception:
        # If robots.txt can't be read, err on the side of skipping rather
        # than assuming access is fine.
        return True

def _ddgs_library(query: str, max_results: int) -> list[dict]:
    """Preferred path: the `duckduckgo_search` (or its `ddgs` successor) package."""
    try:
        from ddgs import DDGS          # package was renamed; try the new name first
    except ImportError:
        from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return [{"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")} for r in results]

def _ddg_html_fallback(query: str, max_results: int) -> list[dict]:
    """No-dependency fallback: DuckDuckGo's plain HTML endpoint, used only if the
    library above is missing, errors, or gets rate-limited."""
    resp = httpx.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=10, follow_redirects=True, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    out = []
    for a in soup.select("a.result__a")[:max_results]:
        href = a.get("href", "")
        m = re.search(r"uddg=([^&]+)", href)          # DDG wraps result URLs in a redirect
        url = unquote(m.group(1)) if m else href
        snippet_el = a.find_parent("div", class_="result__body")
        snippet = snippet_el.select_one(".result__snippet") if snippet_el else None
        out.append({"title": a.get_text(strip=True), "url": url, "snippet": snippet.get_text(strip=True) if snippet else ""})
    return out

def duckduckgo_search(query: str, max_results: int = 8) -> list[dict]:
    try:
        results = _ddgs_library(query, max_results)
        if results:
            return results
    except Exception:
        pass
    return _ddg_html_fallback(query, max_results)     # library missing/blocked/empty -> try the plain endpoint

PROVIDERS = {
    "duckduckgo": duckduckgo_search,
}

def search(query: str, provider: str = "duckduckgo", max_results: int = 8, use_cache: bool = True) -> list[dict]:
    with db.get_conn() as conn:
        if use_cache:
            row = conn.execute(
                "SELECT results_json, fetched_at FROM search_cache WHERE query=? AND provider=?",
                (query, provider),
            ).fetchone()
            if row and (db.now() - row["fetched_at"] < 3600 * 6):
                return db.loads(row["results_json"])

    fn = PROVIDERS.get(provider, duckduckgo_search)
    try:
        results = fn(query, max_results=max_results)
    except Exception as e:
        raise SearchError(f"{provider} search failed ({type(e).__name__}): {e}") from e
    if not results:
        raise SearchError(f"{provider} returned no results for this query.")

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO search_cache (query, provider, results_json, fetched_at) VALUES (?,?,?,?) "
            "ON CONFLICT(query) DO UPDATE SET provider=excluded.provider, results_json=excluded.results_json, fetched_at=excluded.fetched_at",
            (query, provider, db.dumps(results), db.now()),
        )
    return results

def is_public_http_url(url: str) -> bool:
    """SSRF guard: only http(s) URLs whose host resolves to public addresses."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False

def _render_with_browser(url: str) -> Optional[str]:
    """Optional headless-browser fetch for JavaScript-heavy pages.
    Needs `pip install playwright && playwright install chromium`;
    silently unavailable otherwise."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=settings.user_agent)
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            html = page.content()
            browser.close()
        return html
    except Exception:
        return None

def fetch_and_extract(url: str) -> Optional[dict]:
    """Fetch a page and extract clean text, respecting robots.txt and rate limits.
    All extracted text is treated as untrusted data -- see sanitize_webpage_content."""
    if not is_public_http_url(url) or not _robots_allowed(url):
        return None
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False) if downloaded else None
        if not text or len(text) < 400:  # empty/JS-rendered page -> try the optional browser
            html = _render_with_browser(url)
            if html:
                text = trafilatura.extract(html, include_comments=False, include_tables=False) or text
        if not text:
            return None
    except Exception:
        return None
    time.sleep(settings.request_delay_seconds)
    tier, source_type = classify_source(url)
    return {
        "url": url,
        "text": sanitize_webpage_content(text),
        "trust_tier": tier,
        "source_type": source_type,
        "content_hash": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest(),
        "fetched_at": db.now(),
    }

def sanitize_webpage_content(text: str, max_chars: int = 20000) -> str:
    """Web content is data, never instructions. We don't execute anything
    found in it; we simply cap its length and wrap it (the wrapping/labeling
    happens at prompt-build time in brain.py) before it ever reaches a model."""
    return text[:max_chars]
