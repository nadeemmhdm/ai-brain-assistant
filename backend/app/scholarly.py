"""Free scholarly discovery providers used by Trusted Topic Learning.

These providers add structured academic evidence to normal web discovery.
They are optional: network/rate-limit failures simply return no results.
No paid API key is required for Crossref or OpenAlex public endpoints.
"""
from __future__ import annotations

import html
from urllib.parse import quote
import httpx

UA = "AI-Brain-Assistant/0.6 (local research client)"


def _get(url: str, params: dict | None = None) -> dict:
    r = httpx.get(url, params=params, timeout=12, follow_redirects=True, headers={"User-Agent": UA, "Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def crossref(query: str, limit: int = 5) -> list[dict]:
    try:
        data = _get("https://api.crossref.org/works", {"query": query, "rows": min(limit, 10), "select": "DOI,title,URL,abstract,published,type,publisher"})
        out = []
        for item in data.get("message", {}).get("items", []):
            title = " ".join(item.get("title") or []).strip()
            abstract = html.unescape(item.get("abstract") or "")
            abstract = abstract.replace("<jats:p>", " ").replace("</jats:p>", " ")
            doi = item.get("DOI")
            if not title or not doi:
                continue
            out.append({
                "title": title, "url": f"https://doi.org/{doi}", "snippet": abstract[:1200],
                "trust_tier": "A", "source_type": "scholarly metadata/Crossref",
                "provider": "crossref", "identifier": doi,
            })
        return out
    except Exception:
        return []


def openalex(query: str, limit: int = 5) -> list[dict]:
    try:
        data = _get("https://api.openalex.org/works", {"search": query, "per-page": min(limit, 10)})
        out = []
        for item in data.get("results", []):
            title = (item.get("title") or "").strip()
            ids = item.get("ids") or {}
            url = ids.get("doi") or item.get("id")
            if not title or not url:
                continue
            inv = item.get("abstract_inverted_index") or {}
            words = sorted(((pos, word) for word, positions in inv.items() for pos in positions), key=lambda x: x[0])
            abstract = " ".join(w for _, w in words)
            out.append({
                "title": title, "url": url, "snippet": abstract[:1200],
                "trust_tier": "A", "source_type": "scholarly index/OpenAlex",
                "provider": "openalex", "identifier": item.get("id"),
            })
        return out
    except Exception:
        return []


def discover(query: str, per_provider: int = 4) -> list[dict]:
    """Merge free scholarly providers, de-duplicating DOI/URL."""
    merged, seen = [], set()
    for provider in (crossref, openalex):
        for row in provider(query, per_provider):
            key = (row.get("url") or "").lower()
            if key and key not in seen:
                seen.add(key); merged.append(row)
    return merged
