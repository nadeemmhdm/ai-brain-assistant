"""
Search-mode research pipeline (quick / deep).

  recall  -> is there already a good saved answer in the AI Brain?
  plan    -> (deep) the small agent model proposes 2-3 search queries
  search  -> free provider (DuckDuckGo by default), tier-ranked
  read    -> fetch pages (robots.txt + SSRF guarded, optional browser)
  rank    -> split into passages, keep the ones most similar to the question
  answer  -> caller feeds the numbered passages to the main model

Everything fetched is untrusted DATA. It is labelled, numbered and length
limited here; the caller's system prompt tells the model never to follow
instructions found inside it.
"""
import asyncio
import re
import time
from urllib.parse import urlparse
from . import db, brain, search, llm_client
from .search import SearchError

FRESHNESS_WORDS = re.compile(r"\b(today|tonight|latest|current(ly)?|now|news|price|score|weather|this (week|month|year)|20\d\d)\b", re.I)
MEMORY_MAX_AGE_DAYS = 14

MODES = {
    "quick": {"queries": 1, "pages": 5, "passages": 7},
    "deep":  {"queries": 3, "pages": 7, "passages": 11},
}
TIER_BONUS = {"A": 0.10, "B": 0.05, "C": 0.0, "D": -0.05}

def _recall_threshold() -> float:
    return 0.80 if brain.embedding_signature().startswith("st-") else 0.55

def _source_row(url: str, title: str | None, tier: str, source_type: str, content_hash: str, fetched_at: float) -> str:
    with db.get_conn() as conn:
        row = conn.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
        if row:
            conn.execute("UPDATE sources SET fetched_at=?, content_hash=? WHERE id=?", (fetched_at, content_hash, row["id"]))
            return row["id"]
        sid = db.new_id()
        conn.execute(
            "INSERT INTO sources (id, url, title, source_type, trust_tier, fetched_at, content_hash) VALUES (?,?,?,?,?,?,?)",
            (sid, url, title, source_type, tier, fetched_at, content_hash),
        )
        return sid

def _load_sources(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    with db.get_conn() as conn:
        q = ",".join("?" * len(ids))
        rows = conn.execute(f"SELECT * FROM sources WHERE id IN ({q})", ids).fetchall()
    return [dict(r) for r in rows]

def recall(question: str) -> dict | None:
    """Best saved research answer for this question, if it is close enough
    and (for time-sensitive questions) fresh enough to trust."""
    hits = brain.search_knowledge(question, topic="Search memory", top_k=1)
    if not hits:
        return None
    hit = hits[0]
    if hit["score"] < _recall_threshold():
        return None
    age_days = (time.time() - (hit.get("updated_at") or 0)) / 86400
    if age_days > MEMORY_MAX_AGE_DAYS:
        return None
    if FRESHNESS_WORDS.search(question) and age_days > 0.5:
        return None
    return hit

def _lexical(question: str, passage: str) -> float:
    """Share of the question's key words that appear in the passage (catches exact terms embeddings blur)."""
    q = set(brain._tokens(question))
    return len(q & set(brain._tokens(passage))) / len(q) if q else 0.0

def confidence(scored: list[float], tiers: list[str], domains: int) -> dict:
    """A simple, explainable label -- not a probability."""
    best = max(scored) if scored else 0
    pts = (2 if best >= 0.55 else 1 if best >= 0.35 else 0) + (2 if domains >= 3 else 1 if domains == 2 else 0) + (1 if "A" in tiers or "B" in tiers else 0)
    label = "high" if pts >= 4 else "medium" if pts >= 2 else "low"
    return {"label": label, "sources": len(tiers), "domains": domains, "best_tier": min(tiers) if tiers else None}

def _chunks(text: str, size: int = 700) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n{1,}", text) if len(p.strip()) > 60]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) < size:
            cur = f"{cur} {p}".strip()
        else:
            if cur:
                out.append(cur)
            cur = p[:size * 2]
    if cur:
        out.append(cur)
    return out

async def _plan_queries(question: str, n: int) -> list[str]:
    if n <= 1:
        return [question]
    raw = await llm_client.complete(
        "agent",
        [{"role": "system", "content": "Reply with ONLY a JSON array of short web search queries. No prose."},
         {"role": "user", "content": f"Give {n} different search queries that would help answer: {question}"}],
        reasoning_level="off",
    )
    import json
    try:
        qs = json.loads(raw[raw.find("["):raw.rfind("]") + 1])
        qs = [str(q)[:120] for q in qs if str(q).strip()][:n]
        return list(dict.fromkeys([question] + qs))[:n]
    except Exception:
        return [question]

async def run(question: str, mode: str, emit, online: bool = True) -> dict:
    """Returns {"blocks": [...], "sources": [...], "from_memory": bool, "save": {...}|None}.
    `emit(stage, detail)` is an async callback used for live progress."""
    cfg = MODES.get(mode, MODES["quick"])

    await emit("recall", "Checking what I already know…")
    hit = recall(question) if mode != "deep" else None
    if hit:
        srcs = _load_sources(hit["source_ids"] or [])
        for i, s in enumerate(srcs, 1):
            s["index"] = i
        await emit("recalled", "Found a saved answer from earlier research")
        return {
            "blocks": [f"[Saved research — {hit['verification_status']}]\nQ: {hit['question']}\nA: {hit['answer']}"],
            "sources": srcs, "from_memory": True, "save": None,
            "confidence": {"label": "medium" if hit["verification_status"] == "verified" else "low", "sources": len(srcs), "domains": len(srcs), "best_tier": None, "from_memory": True},
            "context_text": hit["answer"],
        }

    if not online:
        await emit("offline", "Offline mode — using only what's saved locally")
        return {"blocks": [], "sources": [], "from_memory": False, "save": None}

    queries = await _plan_queries(question, cfg["queries"]) if mode == "deep" else [question]
    await emit("searching", f"Searching the web ({len(queries)} quer{'y' if len(queries)==1 else 'ies'})…")

    results, seen, search_errors = [], set(), []
    for q in queries:
        try:
            for r in await asyncio.to_thread(search.search, q, "duckduckgo", cfg["pages"] * 2):
                url = r.get("url")
                if url and url not in seen:
                    seen.add(url); results.append(r)
        except SearchError as e:
            search_errors.append(str(e))

    if not results:
        detail = "Web search didn't return anything" + (f" ({search_errors[0]})" if search_errors else "") + " -- answering from what I already know."
        await emit("notice", detail)
        return {"blocks": [], "sources": [], "from_memory": False, "save": None, "confidence": None, "context_text": ""}
    for r in results:
        r["tier"], r["stype"] = search.classify_source(r["url"])
    results.sort(key=lambda r: "ABCD".index(r["tier"]))

    pages = []
    for r in results:
        if len(pages) >= cfg["pages"]:
            break
        await emit("reading", f"Reading {urlparse(r['url']).netloc}…", {"done": len(pages), "total": cfg["pages"]})
        page = await asyncio.to_thread(search.fetch_and_extract, r["url"])
        if page:
            page["title"] = r.get("title") or r["url"]
            pages.append(page)
        elif r.get("snippet"):
            # page blocked/unreadable: fall back to the search snippet, clearly short
            pages.append({"url": r["url"], "title": r.get("title") or r["url"], "text": r["snippet"],
                          "trust_tier": r["tier"], "source_type": r["stype"], "content_hash": "", "fetched_at": time.time()})

    await emit("ranking", "Picking the most relevant passages…")
    qvec = brain.embed(question)
    cands = []
    for pi, page in enumerate(pages):
        ch = _chunks(page["text"]) or [page["text"][:700]]
        vecs = brain.embed_many(ch)
        for c, v in zip(ch, vecs):
            score = 0.7 * brain.cosine(qvec, v) + 0.3 * _lexical(question, c) + TIER_BONUS.get(page["trust_tier"], 0)
            cands.append((score, pi, c))
    cands.sort(key=lambda x: x[0], reverse=True)

    chosen, used_norm, chosen_scores = [], [], []
    for score, pi, c in cands:
        norm = re.sub(r"\W+", "", c.lower())[:120]
        if any(norm[:60] == u[:60] for u in used_norm):
            continue  # near-duplicate passage
        used_norm.append(norm); chosen.append((pi, c)); chosen_scores.append(score)
        if len(chosen) >= cfg["passages"]:
            break

    # number sources in order of first use so [n] in the answer matches the UI
    order: list[int] = []
    for pi, _ in chosen:
        if pi not in order:
            order.append(pi)
    sources, blocks, idx_of = [], [], {}
    for n, pi in enumerate(order, 1):
        p = pages[pi]
        sid = _source_row(p["url"], p["title"], p["trust_tier"], p["source_type"], p["content_hash"], p["fetched_at"])
        idx_of[pi] = n
        sources.append({"id": sid, "index": n, "url": p["url"], "title": p["title"],
                        "trust_tier": p["trust_tier"], "source_type": p["source_type"], "fetched_at": p["fetched_at"]})
    for pi, c in chosen:
        p = pages[pi]
        blocks.append(f"[{idx_of[pi]}] ({p['title']} — trust {p['trust_tier']})\n{c}")

    domains = {urlparse(s["url"]).netloc.removeprefix("www.") for s in sources}
    return {
        "blocks": blocks, "sources": sources, "from_memory": False,
        "save": {"source_ids": [s["id"] for s in sources], "domains": len(domains)},
        "confidence": confidence(chosen_scores, [s["trust_tier"] for s in sources], len(domains)),
        "context_text": "\n".join(blocks),
    }
