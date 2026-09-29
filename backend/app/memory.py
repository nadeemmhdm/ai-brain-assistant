"""
Memory = two things, both local:

1. User memories -- short facts/preferences the user explicitly asked the
   assistant to keep ("remember that I prefer metric units"). Managed in
   the UI and injected into the prompt when relevant.
2. Research memory -- answers found by Search mode are saved into the AI
   Brain (with their sources) so the same or a similar question can be
   answered next time from disk, quickly and offline.

Nothing is remembered silently except research answers, and the user can
turn that off (setting `remember_research`) or delete any item.
"""
import re
from . import db, brain
from .routers.settings_router import get_value

_REMEMBER_RE = re.compile(r"^\s*(?:please\s+)?(?:remember|note|keep in mind)\s+(?:that\s+)?(.{4,300})$", re.I | re.S)

def extract_explicit(text: str) -> str | None:
    """Only an explicit 'remember that ...' request creates a memory."""
    m = _REMEMBER_RE.match(text.strip())
    return m.group(1).strip().rstrip(".") if m else None

def add(content: str) -> str:
    mid = db.new_id()
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO memories (id, content, embedding, created_at) VALUES (?,?,?,?)",
            (mid, content, brain.embed(content).tobytes(), db.now()),
        )
    return mid

def list_all() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, content, created_at, last_used_at, use_count FROM memories ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def delete(mid: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM memories WHERE id=?", (mid,))

def relevant(query: str, limit: int = 5) -> list[str]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, content, embedding FROM memories").fetchall()
    if not rows:
        return []
    if len(rows) <= limit:
        chosen = [r["content"] for r in rows]
        ids = [r["id"] for r in rows]
    else:
        import numpy as np
        q = brain.embed(query)
        scored = sorted(rows, key=lambda r: brain.cosine(q, np.frombuffer(r["embedding"], dtype=np.float32)), reverse=True)[:limit]
        chosen = [r["content"] for r in scored]
        ids = [r["id"] for r in scored]
    with db.get_conn() as conn:
        conn.executemany("UPDATE memories SET use_count=use_count+1, last_used_at=? WHERE id=?", [(db.now(), i) for i in ids])
    return chosen

# ---- research memory (stored in the AI Brain) -----------------------------
RESEARCH_TOPIC = "Search memory"

def remember_research_enabled() -> bool:
    return get_value("remember_research") != "false"

def save_research(question: str, answer: str, source_ids: list[str], distinct_domains: int) -> str:
    verification = "verified" if distinct_domains >= 2 else "unverified"
    summary = answer[:200] + ("..." if len(answer) > 200 else "")
    return brain.add_knowledge(
        topic=RESEARCH_TOPIC, subtopic=None, question=question, answer=answer,
        summary=summary, source_ids=source_ids, verification_status=verification,
    )
