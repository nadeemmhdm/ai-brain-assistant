"""
Search-provider abstraction (section 26 of the spec). Default provider is
DuckDuckGo, which needs no API key. Adding a new provider means adding one
function and registering it in PROVIDERS -- nothing else in the app
depends on which provider is active.
"""
import time
import hashlib
import urllib.robotparser as robotparser
from urllib.parse import urlparse
from typing import Optional
import httpx
import trafilatura
from .config import settings
from . import db

# --- trust tiers (section 5) --------------------------------------------
TIER_A_HINTS = (".gov", ".edu", "w3.org", "ietf.org", "iso.org", "nist.gov",
                "who.int", "un.org", "arxiv.org", "docs.python.org", "developer.mozilla.org")
TIER_B_HINTS = ("wikipedia.org", "owasp.org", "ieee.org", "acm.org", "readthedocs.io")
TIER_D_HINTS = ("reddit.com", "quora.com", "forum", "answers.")

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

def duckduckgo_search(query: str, max_results: int = 8) -> list[dict]:
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return [{"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")} for r in results]

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
        return [{"title": None, "url": None, "snippet": f"Search failed: {e}", "error": True}]

    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO search_cache (query, provider, results_json, fetched_at) VALUES (?,?,?,?) "
            "ON CONFLICT(query) DO UPDATE SET provider=excluded.provider, results_json=excluded.results_json, fetched_at=excluded.fetched_at",
            (query, provider, db.dumps(results), db.now()),
        )
    return results

def fetch_and_extract(url: str) -> Optional[dict]:
    """Fetch a page and extract clean text, respecting robots.txt and rate limits.
    All extracted text is treated as untrusted data -- see sanitize_webpage_content."""
    if not _robots_allowed(url):
        return None
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
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

def sanitize_webpage_content(text: str, max_chars: int = 6000) -> str:
    """Web content is data, never instructions. We don't execute anything
    found in it; we simply cap its length and wrap it (the wrapping/labeling
    happens at prompt-build time in brain.py) before it ever reaches a model."""
    return text[:max_chars]
