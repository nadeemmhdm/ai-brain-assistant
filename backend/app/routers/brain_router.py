from fastapi import APIRouter
from .. import brain, db

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

@router.get("/sessions")
def sessions():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, topic, status, stats_json, started_at, finished_at FROM learning_sessions ORDER BY started_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["stats"] = db.loads(d.pop("stats_json"))
        out.append(d)
    return out
