"""
Training dataset generation from the AI Brain (spec section 20).

Converts verified (and, if requested, unverified/conflicted) knowledge
items into instruction/input/output examples, stored separately from the
knowledge base so the user can review and approve them before any
training run touches them. This step never modifies model weights --
see training.py for the (separate, explicit) step that does.
"""
from . import db

def create_dataset(name: str, topic: str | None = None, only_verified: bool = True) -> dict:
    did = db.new_id()
    with db.get_conn() as conn:
        sql = "SELECT * FROM knowledge"
        conditions, params = [], []
        if topic:
            conditions.append("topic = ?")
            params.append(topic)
        if only_verified:
            conditions.append("verification_status = 'verified'")
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        rows = conn.execute(sql, params).fetchall()

        conn.execute(
            "INSERT INTO datasets (id, name, topic, status, created_at) VALUES (?,?,?,?,?)",
            (did, name, topic, "draft", db.now()),
        )
        for row in rows:
            iid = db.new_id()
            conn.execute(
                "INSERT INTO dataset_items (id, dataset_id, instruction, input, output, approved, source_knowledge_id) "
                "VALUES (?,?,?,?,?,?,?)",
                (iid, did, row["question"], f"Explain in the context of {row['subtopic'] or row['topic']}.",
                 row["answer"], 1, row["id"]),
            )
    return {"id": did, "name": name, "item_count": len(rows)}

def list_datasets() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM dataset_items WHERE dataset_id=d.id) as item_count, "
            "(SELECT COUNT(*) FROM dataset_items WHERE dataset_id=d.id AND approved=1) as approved_count "
            "FROM datasets d ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

def get_items(dataset_id: str) -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM dataset_items WHERE dataset_id=?", (dataset_id,)).fetchall()
    return [dict(r) for r in rows]

def set_item_approved(item_id: str, approved: bool):
    with db.get_conn() as conn:
        conn.execute("UPDATE dataset_items SET approved=? WHERE id=?", (1 if approved else 0, item_id))

def delete_dataset(dataset_id: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM dataset_items WHERE dataset_id=?", (dataset_id,))
        conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))

def export_jsonl(dataset_id: str, approved_only: bool = True) -> list[dict]:
    """Alpaca-style {instruction, input, output} records, ready for a
    standard LoRA/QLoRA fine-tuning script (see training.py)."""
    items = get_items(dataset_id)
    if approved_only:
        items = [i for i in items if i["approved"]]
    return [{"instruction": i["instruction"], "input": i["input"], "output": i["output"]} for i in items]


def clone_dataset(dataset_id: str, name_suffix: str = " · cloud refined") -> dict:
    """Create a derived local dataset so cloud refinement never overwrites the reviewed original."""
    with db.get_conn() as conn:
        src = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        if not src:
            raise ValueError("Unknown dataset")
        did = db.new_id()
        name = f"{src['name']}{name_suffix}"
        conn.execute("INSERT INTO datasets (id,name,topic,status,created_at) VALUES (?,?,?,?,?)",
                     (did, name, src["topic"], "draft", db.now()))
        rows = conn.execute("SELECT * FROM dataset_items WHERE dataset_id=? AND approved=1", (dataset_id,)).fetchall()
        for row in rows:
            conn.execute("INSERT INTO dataset_items (id,dataset_id,instruction,input,output,approved,source_knowledge_id) VALUES (?,?,?,?,?,?,?)",
                         (db.new_id(), did, row["instruction"], row["input"], row["output"], 1, row["source_knowledge_id"]))
    return {"id": did, "name": name, "item_count": len(rows), "source_dataset_id": dataset_id}
