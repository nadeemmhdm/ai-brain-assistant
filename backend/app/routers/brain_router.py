from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import brain, db, teach

router = APIRouter(prefix="/api/brain", tags=["brain"])

@router.get("")
def stats():
    return brain.brain_stats()

@router.get("/topics")
def topics():
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT topic, COUNT(*) as items, SUM(CASE WHEN verification_status='verified' THEN 1 ELSE 0 END) as verified "
            "FROM knowledge GROUP BY topic ORDER BY items DESC"
        ).fetchall()
    return [dict(r) for r in rows]

@router.get("/knowledge")
def knowledge(query: str = "", topic: str = None, limit: int = 20):
    if query:
        return brain.search_knowledge(query, topic=topic, top_k=limit)
    with db.get_conn() as conn:
        sql = "SELECT id, topic, subtopic, question, summary, verification_status FROM knowledge"
        params = []
        if topic:
            sql += " WHERE topic=?"
            params.append(topic)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]

@router.delete("/knowledge/{kid}")
def delete_knowledge(kid: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM knowledge WHERE id=?", (kid,))
    return {"ok": True}

@router.get("/sources")
def sources(limit: int = 50):
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM sources ORDER BY fetched_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def _session_is_empty_or_failed(status: str, stats: dict) -> bool:
    return status in ("error", "failed") or int((stats or {}).get("knowledge_items") or 0) <= 0

@router.get("/sessions")
def sessions():
    # Failed/zero-result learning attempts are transient diagnostics, not useful
    # Brain history. Clean legacy rows as well as keeping future history clean.
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, topic, status, stats_json, started_at, finished_at FROM learning_sessions ORDER BY started_at DESC").fetchall()
        out = []
        stale = []
        for r in rows:
            d = dict(r)
            d["stats"] = db.loads(d.pop("stats_json")) or {}
            if _session_is_empty_or_failed(d["status"], d["stats"]):
                stale.append(d["id"])
            else:
                out.append(d)
        if stale:
            conn.executemany("DELETE FROM learning_sessions WHERE id=?", [(sid,) for sid in stale])
    return out

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    with db.get_conn() as conn:
        cur = conn.execute("DELETE FROM learning_sessions WHERE id=?", (session_id,))
    if not cur.rowcount:
        raise HTTPException(404, "Learning history item not found")
    return {"ok": True}


# ---- manual training: teach / import ------------------------------------------
class TeachBody(BaseModel):
    topic: str
    question: str
    answer: str

@router.post("/teach")
def teach_item(body: TeachBody):
    if len(body.question.strip()) < 3 or len(body.answer.strip()) < 3:
        raise HTTPException(400, "Add a question and an answer.")
    return {"id": teach.teach(body.topic, body.question, body.answer)}

class ImportBody(BaseModel):
    topic: str
    title: str
    text: str

@router.post("/import")
def import_text(body: ImportBody):
    try:
        return {"chunks": teach.import_text(body.topic, body.title or "Imported note", body.text)}
    except ValueError as e:
        raise HTTPException(400, str(e))

# ---- automatic training: watch-list ------------------------------------------
class WatchBody(BaseModel):
    topic: str
    interval_hours: int = 168

@router.get("/watch")
def watch_list():
    return teach.list_watch()

@router.post("/watch")
def watch_add(body: WatchBody):
    if len(body.topic.strip()) < 2:
        raise HTTPException(400, "Enter a topic.")
    return {"id": teach.add_watch(body.topic, body.interval_hours)}

class EnableBody(BaseModel):
    enabled: bool

@router.patch("/watch/{wid}")
def watch_toggle(wid: str, body: EnableBody):
    teach.set_enabled(wid, body.enabled)
    return {"ok": True}

@router.delete("/watch/{wid}")
def watch_remove(wid: str):
    teach.remove_watch(wid)
    return {"ok": True}
