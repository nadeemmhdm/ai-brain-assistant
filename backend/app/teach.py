"""
Manual + automatic Brain training (knowledge, not model weights).

Manual : teach a fact/Q&A yourself, or import a text/markdown file.
Auto   : a watch-list of topics is re-researched on a schedule (weekly by
         default) while the app is running, online and not busy.
"""
import asyncio
import re
import time
from . import db, brain, learn

MAX_IMPORT_CHARS = 500_000

def teach(topic: str, question: str, answer: str, subtopic: str | None = None) -> str:
    return brain.add_knowledge(topic=topic.strip()[:80] or "General", subtopic=subtopic, question=question.strip()[:300],
                               answer=answer.strip()[:4000], summary=answer.strip()[:200],
                               source_ids=[], verification_status="user-provided")

def _split(text: str, size: int = 900) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}".strip()
        else:
            if cur: out.append(cur)
            while len(p) > size:                 # very long paragraph
                out.append(p[:size]); p = p[size:]
            cur = p
    if cur: out.append(cur)
    return out

def import_text(topic: str, title: str, text: str) -> int:
    if len(text) > MAX_IMPORT_CHARS:
        raise ValueError("That file is too large (max ~500 KB of text).")
    chunks = _split(text)
    for i, c in enumerate(chunks, 1):
        brain.add_knowledge(topic=topic.strip()[:80] or "Imported", subtopic=title[:80], question=f"{title} (part {i})",
                            answer=c, summary=c[:200], source_ids=[], verification_status="user-provided")
    return len(chunks)

# ---- schedule ----------------------------------------------------------------
def list_watch() -> list[dict]:
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM autolearn_topics ORDER BY topic").fetchall()]

def add_watch(topic: str, interval_hours: int) -> str:
    wid = db.new_id()
    with db.get_conn() as conn:
        conn.execute("INSERT INTO autolearn_topics (id, topic, interval_hours, enabled) VALUES (?,?,?,1) "
                     "ON CONFLICT(topic) DO UPDATE SET interval_hours=excluded.interval_hours, enabled=1", (wid, topic.strip()[:80], max(1, min(interval_hours, 24 * 90))))
    return wid

def set_enabled(wid: str, enabled: bool):
    with db.get_conn() as conn:
        conn.execute("UPDATE autolearn_topics SET enabled=? WHERE id=?", (1 if enabled else 0, wid))

def remove_watch(wid: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM autolearn_topics WHERE id=?", (wid,))

def due() -> dict | None:
    now = time.time()
    with db.get_conn() as conn:
        for r in conn.execute("SELECT * FROM autolearn_topics WHERE enabled=1 ORDER BY COALESCE(last_run,0)").fetchall():
            if not r["last_run"] or now - r["last_run"] >= r["interval_hours"] * 3600:
                return dict(r)
    return None

async def scheduler_loop(is_online, models_ready):
    """Runs forever in the background. Waits for a quiet, online moment."""
    await asyncio.sleep(60)
    while True:
        try:
            item = due()
            if item and not learn.any_running() and await is_online() and await models_ready():
                learn.start_session(item["topic"])
                with db.get_conn() as conn:
                    conn.execute("UPDATE autolearn_topics SET last_run=?, last_status='started' WHERE id=?", (time.time(), item["id"]))
        except Exception:
            pass
        await asyncio.sleep(300)
