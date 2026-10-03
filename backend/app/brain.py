"""
The AI Brain: local knowledge storage + retrieval (sections 12-14, 17-18).

Embeddings: tries to use `sentence-transformers` (all-MiniLM-L6-v2) if it's
installed locally; if not, falls back to a dependency-free hashed
bag-of-words vector so the whole system still works with zero extra
downloads. Nothing is ever sent to an external embedding API.
"""
import zlib
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

def embedding_signature() -> str:
    """Identifies the embedding scheme. If it changes (e.g. you install
    sentence-transformers), stored vectors are re-computed on startup so
    old and new vectors are never compared with each other."""
    return "st-minilm-v1" if _get_model() is not None else f"hash-v2-{_EMBED_DIM}"

def _hash_embed(text: str) -> np.ndarray:
    # NOTE: zlib.crc32 is stable across processes/restarts. (Python's
    # built-in hash() is randomized per process, which would silently
    # corrupt any vectors saved to disk.)
    vec = np.zeros(_EMBED_DIM, dtype=np.float32)
    for tok in _tokens(text):
        vec[zlib.crc32(tok.encode("utf-8")) % _EMBED_DIM] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

_STOP = set("a an the is are was were be been of to in on for and or it this that what how why who when where do does did with as by at from".split())
def _tokens(text: str):
    import re
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]

def embed(text: str) -> np.ndarray:
    model = _get_model()
    if model is not None:
        vec = model.encode([text])[0]
        return vec.astype(np.float32)
    return _hash_embed(text)

def embed_many(texts: list[str]) -> list[np.ndarray]:
    model = _get_model()
    if model is not None and texts:
        return [v.astype(np.float32) for v in model.encode(texts)]
    return [_hash_embed(t) for t in texts]

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return _cosine(a, b)

def reembed_if_needed():
    """Called at startup. Re-embeds stored knowledge/memories when the
    embedding scheme changed since they were saved."""
    sig = embedding_signature()
    with db.get_conn() as conn:
        row = conn.execute("SELECT value FROM kv_settings WHERE key='embed_sig'").fetchone()
        if row and row["value"] == sig:
            return 0
        n = 0
        for r in conn.execute("SELECT id, topic, subtopic, question, answer FROM knowledge").fetchall():
            v = embed(f"{r['topic']} {r['subtopic'] or ''} {r['question']} {r['answer']}")
            conn.execute("UPDATE knowledge SET embedding=? WHERE id=?", (v.tobytes(), r["id"])); n += 1
        for r in conn.execute("SELECT id, content FROM memories").fetchall():
            conn.execute("UPDATE memories SET embedding=? WHERE id=?", (embed(r["content"]).tobytes(), r["id"])); n += 1
        conn.execute("INSERT INTO kv_settings (key,value) VALUES ('embed_sig',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (sig,))
    return n

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
        semantic = _cosine(qvec, vec)
        query_tokens = set(_tokens(query))
        row_tokens = set(_tokens(f"{row['topic']} {row['subtopic'] or ''} {row['question']} {row['summary'] or ''}"))
        lexical = len(query_tokens & row_tokens) / len(query_tokens) if query_tokens else 0.0
        verified_bonus = 0.035 if row["verification_status"] in ("verified", "teacher_verified") else (-0.08 if row["verification_status"] == "conflict" else 0.0)
        score = 0.78 * semantic + 0.22 * lexical + verified_bonus
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
            "updated_at": row["updated_at"],
        })
    return out

def brain_stats() -> dict:
    with db.get_conn() as conn:
        topics = conn.execute("SELECT COUNT(DISTINCT topic) c FROM knowledge").fetchone()["c"]
        items = conn.execute("SELECT COUNT(*) c FROM knowledge").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) c FROM knowledge WHERE verification_status IN ('verified','teacher_verified')").fetchone()["c"]
        conflicts = conn.execute("SELECT COUNT(*) c FROM knowledge WHERE verification_status='conflict'").fetchone()["c"]
        sources = conn.execute("SELECT COUNT(*) c FROM sources").fetchone()["c"]
        last_session = conn.execute("SELECT topic, finished_at FROM learning_sessions ORDER BY started_at DESC LIMIT 1").fetchone()
    return {
        "total_topics": topics, "total_knowledge_items": items, "verified_knowledge": verified,
        "conflicting_knowledge": conflicts, "total_sources": sources,
        "embedding_backend": "sentence-transformers" if _get_model() else "hashed-fallback",
        "embedding_signature": embedding_signature(),
        "last_learning_session": dict(last_session) if last_session else None,
    }
