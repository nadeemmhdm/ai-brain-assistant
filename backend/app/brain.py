"""
The AI Brain: local knowledge storage + retrieval (sections 12-14, 17-18).

Embeddings: tries to use `sentence-transformers` (all-MiniLM-L6-v2) if it's
installed locally; if not, falls back to a dependency-free hashed
bag-of-words vector so the whole system still works with zero extra
downloads. Nothing is ever sent to an external embedding API.
"""
import numpy as np
from typing import Optional
from . import db

_EMBED_DIM = 256
_model = None
_model_checked = False

def _get_model():
    global _model, _model_checked
    if _model_checked:
        return _model
    _model_checked = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _model = None
    return _model

def embed(text: str) -> np.ndarray:
    model = _get_model()
    if model is not None:
        vec = model.encode([text])[0]
        return vec.astype(np.float32)
    # Fallback: hashed bag-of-words, no downloads required.
    vec = np.zeros(_EMBED_DIM, dtype=np.float32)
    for tok in text.lower().split():
        vec[hash(tok) % _EMBED_DIM] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0

def add_knowledge(topic, subtopic, question, answer, summary, source_ids, verification_status="unverified", conflict=None):
    kid = db.new_id()
    vec = embed(f"{topic} {subtopic} {question} {answer}")
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO knowledge (id, topic, subtopic, question, answer, summary, embedding, "
            "source_ids_json, verification_status, conflict_json, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (kid, topic, subtopic, question, answer, summary, vec.tobytes(),
             db.dumps(source_ids), verification_status, db.dumps(conflict), db.now(), db.now()),
        )
    return kid

def search_knowledge(query: str, topic: Optional[str] = None, top_k: int = 5) -> list[dict]:
    qvec = embed(query)
    with db.get_conn() as conn:
        sql = "SELECT * FROM knowledge"
        params = []
        if topic:
            sql += " WHERE topic = ?"
            params.append(topic)
        rows = conn.execute(sql, params).fetchall()

    scored = []
    for row in rows:
        vec = np.frombuffer(row["embedding"], dtype=np.float32)
        score = _cosine(qvec, vec)
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for score, row in scored[:top_k]:
        out.append({
            "id": row["id"], "topic": row["topic"], "subtopic": row["subtopic"],
            "question": row["question"], "answer": row["answer"], "summary": row["summary"],
            "source_ids": db.loads(row["source_ids_json"]),
            "verification_status": row["verification_status"],
            "conflict": db.loads(row["conflict_json"]),
            "score": round(score, 4),
        })
    return out

def brain_stats() -> dict:
    with db.get_conn() as conn:
        topics = conn.execute("SELECT COUNT(DISTINCT topic) c FROM knowledge").fetchone()["c"]
        items = conn.execute("SELECT COUNT(*) c FROM knowledge").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) c FROM knowledge WHERE verification_status='verified'").fetchone()["c"]
        conflicts = conn.execute("SELECT COUNT(*) c FROM knowledge WHERE verification_status='conflict'").fetchone()["c"]
        sources = conn.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"]
        last_session = conn.execute("SELECT topic, finished_at FROM learning_sessions ORDER BY started_at DESC LIMIT 1").fetchone()
    return {
        "total_topics": topics, "total_knowledge_items": items, "verified_knowledge": verified,
        "conflicting_knowledge": conflicts, "total_sources": sources,
        "embedding_backend": "sentence-transformers" if _get_model() else "hashed-fallback",
        "last_learning_session": dict(last_session) if last_session else None,
    }
