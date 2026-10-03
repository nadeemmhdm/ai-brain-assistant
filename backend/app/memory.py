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


# ---- safe local user profile -----------------------------------------------
# These are deliberately narrow, user-stated facts useful for personalization.
# Do not infer or auto-store sensitive traits, secrets, health, politics,
# religion, sexuality, financial data, precise location, or credentials.
_PROFILE_PATTERNS = [
    ("name", re.compile(r"^\s*(?:my name is|call me)\s+([A-Za-z][A-Za-z .'-]{1,60})[.!]?\s*$", re.I)),
    ("learning", re.compile(r"^\s*(?:i(?:'m| am)\s+(?:learning|studying)|i study)\s+(.{2,120})[.!]?\s*$", re.I)),
    ("work", re.compile(r"^\s*(?:i(?:'m| am)\s+working\s+(?:as|on|in)|i work\s+(?:as|on|in))\s+(.{2,120})[.!]?\s*$", re.I)),
    ("interest", re.compile(r"^\s*(?:i(?:'m| am)\s+interested in|i like|i love)\s+(.{2,120})[.!]?\s*$", re.I)),
    ("preference", re.compile(r"^\s*i prefer\s+(.{2,120})[.!]?\s*$", re.I)),
]
_SENSITIVE = re.compile(
    r"\b(password|passphrase|api\s*key|secret|token|otp|pin|credit\s*card|bank|account\s*number|"
    r"aadhaar|passport|medical|diagnos|disease|medication|religion|caste|politic|party|vote|"
    r"sexual|orientation|pregnan|criminal|exact address|home address)\b", re.I
)

def extract_profile_fact(text: str) -> tuple[str, str] | None:
    """Extract only a narrow, explicitly user-stated, non-sensitive profile fact."""
    raw = text.strip()
    if not 3 <= len(raw) <= 220 or _SENSITIVE.search(raw):
        return None
    for kind, pattern in _PROFILE_PATTERNS:
        m = pattern.match(raw)
        if m:
            value = m.group(1).strip().rstrip(".")
            if value and not _SENSITIVE.search(value):
                return kind, value
    return None

def upsert_profile_fact(kind: str, value: str) -> str:
    """Store profile locally. Singleton fields update; interests/preferences accumulate."""
    key = f"user_profile:{kind}"
    if kind in ("name", "learning", "work"):
        with db.get_conn() as conn:
            row = conn.execute("SELECT id FROM memories WHERE content LIKE ?", (key + "=%",)).fetchone()
            content = f"{key}={value}"
            if row:
                conn.execute("UPDATE memories SET content=?, embedding=?, created_at=? WHERE id=?",
                             (content, brain.embed(content).tobytes(), db.now(), row["id"]))
                return row["id"]
    content = f"{key}={value}"
    with db.get_conn() as conn:
        row = conn.execute("SELECT id FROM memories WHERE content=?", (content,)).fetchone()
        if row:
            return row["id"]
    return add(content)

def profile_context(query: str, limit: int = 6) -> list[str]:
    """Return useful profile facts for either local model without exposing storage syntax."""
    with db.get_conn() as conn:
        rows = conn.execute("SELECT content FROM memories WHERE content LIKE 'user_profile:%' ORDER BY created_at DESC").fetchall()
    facts = []
    for r in rows:
        content = r["content"]
        try:
            left, value = content.split("=", 1)
            kind = left.split(":", 1)[1]
        except ValueError:
            continue
        facts.append(f"{kind}: {value}")
    return facts[:limit]
