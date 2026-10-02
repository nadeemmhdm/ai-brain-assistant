"""API-key-free trusted discovery/ranking layer.

This module intentionally does NOT scrape Google Search or Google AI answers.
It discovers candidates through supported no-key search providers, then independently
fetches the original pages and ranks evidence by authority, relevance, independence,
freshness hints and successful full-text extraction.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse
from . import search

PRIMARY_HINTS = (
    ".gov", ".edu", "who.int", "un.org", "nist.gov", "cisa.gov", "ietf.org",
    "rfc-editor.org", "w3.org", "iso.org", "docs.python.org", "developer.mozilla.org",
    "cve.org", "cve.mitre.org", "cwe.mitre.org", "attack.mitre.org",
)
COMMUNITY_HINTS = ("reddit.com", "quora.com", "medium.com", "blogspot.", "forum")

def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")

def authority_score(url: str, tier: str) -> float:
    host = _host(url)
    if any(x in host for x in PRIMARY_HINTS): return 1.0
    if tier == "A": return .92
    if tier == "B": return .74
    if any(x in host for x in COMMUNITY_HINTS): return .20
    return .46

def lexical_score(query: str, text: str) -> float:
    q = {x for x in re.findall(r"[a-z0-9]{2,}", query.lower())}
    if not q: return 0.0
    t = set(re.findall(r"[a-z0-9]{2,}", text.lower()))
    return len(q & t) / len(q)

def discover(query: str, max_results: int = 10) -> list[dict]:
    """Return deduplicated candidates, authority-first, without trusting snippets as facts."""
    raw = search.search(query, "duckduckgo", max_results=max_results, use_cache=True)
    out, seen = [], set()
    for r in raw:
        url = r.get("url") or ""
        host = _host(url)
        if not url or not host or url in seen:
            continue
        seen.add(url)
        tier, stype = search.classify_source(url)
        out.append({**r, "trust_tier": tier, "source_type": stype,
                    "authority_score": authority_score(url, tier), "domain": host})
    out.sort(key=lambda x: (x["authority_score"], lexical_score(query, (x.get("title") or "")+" "+(x.get("snippet") or ""))), reverse=True)
    return out

def collect(query: str, max_results: int = 10, max_pages: int = 6) -> list[dict]:
    """Fetch original pages. A search result ranking alone never makes a source trusted."""
    candidates = discover(query, max_results)
    pages, domains = [], set()
    # First pass favors independent domains, then fills remaining slots.
    ordered = sorted(candidates, key=lambda x: x["authority_score"], reverse=True)
    for r in ordered:
        if len(pages) >= max_pages: break
        page = search.fetch_and_extract(r["url"])
        if not page: continue
        host = r["domain"]
        relevance = lexical_score(query, page.get("text", "")[:6000])
        page.update(title=r.get("title") or r["url"], domain=host,
                    authority_score=r["authority_score"], relevance_score=relevance,
                    discovery_provider="duckduckgo")
        pages.append(page); domains.add(host)
    pages.sort(key=lambda p: (.58*p["authority_score"] + .42*p["relevance_score"]), reverse=True)
    return pages
