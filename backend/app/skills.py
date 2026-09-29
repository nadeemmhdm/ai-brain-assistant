"""
Skills: short, reusable instructions the user can attach to a message
(picked in the composer), like a saved macro. A few trusted built-ins ship
by default; the user can add their own and edit/delete anything (built-ins
are recreated if deleted-then-missing, so the starter set is always there,
but editing a built-in's text sticks).
"""
from . import db

BUILTINS = [
    {"name": "Summarize", "icon": "FileText", "description": "Summarize the text or topic clearly and briefly.",
     "instructions": "Summarize the user's text or topic in a short, clear way: a 1-2 sentence overview, then the key points as a short bullet list. Do not add opinions or information that wasn't in the source."},
    {"name": "Explain simply", "icon": "Lightbulb", "description": "Explain like I'm new to the topic.",
     "instructions": "Explain the topic as simply and clearly as possible, as if to someone new to it. Use short sentences and a everyday analogy if it helps. Avoid jargon, or define it the first time you use it."},
    {"name": "Fix grammar", "icon": "SpellCheck", "description": "Correct grammar and spelling, keep the meaning.",
     "instructions": "Correct the grammar, spelling and punctuation of the user's text without changing its meaning, tone or intent. Return only the corrected text unless asked for an explanation of the changes."},
    {"name": "Translate", "icon": "Languages", "description": "Translate to the language the user names.",
     "instructions": "Translate the user's text into the language they name (or, if none is named, ask which language). Keep the tone and meaning faithful; do not add commentary."},
    {"name": "Brainstorm", "icon": "Sparkles", "description": "Generate varied, concrete ideas.",
     "instructions": "Brainstorm a set of varied, concrete ideas for the user's request. Prefer specific, actionable ideas over vague ones, and briefly note the trade-off of each."},
    {"name": "Code review", "icon": "Code2", "description": "Review code for bugs, clarity and style.",
     "instructions": "Review the given code like a careful, friendly senior engineer: point out real bugs or edge cases first, then readability/style issues, then optional nice-to-haves. Be specific (line/function) and concise; don't rewrite the whole thing unless asked."},
]

def seed():
    with db.get_conn() as conn:
        have = {r["name"] for r in conn.execute("SELECT name FROM skills WHERE builtin=1").fetchall()}
        for b in BUILTINS:
            if b["name"] not in have:
                conn.execute("INSERT INTO skills (id, name, description, instructions, builtin, icon, created_at) VALUES (?,?,?,?,1,?,?)",
                             (db.new_id(), b["name"], b["description"], b["instructions"], b["icon"], db.now()))

def list_all() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM skills ORDER BY builtin DESC, name").fetchall()
    return [dict(r) for r in rows]

def get(sid: str) -> dict | None:
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id=?", (sid,)).fetchone()
    return dict(row) if row else None

def create(name: str, description: str, instructions: str, icon: str = "Sparkles") -> str:
    sid = db.new_id()
    with db.get_conn() as conn:
        conn.execute("INSERT INTO skills (id, name, description, instructions, builtin, icon, created_at) VALUES (?,?,?,?,0,?,?)",
                     (sid, name.strip()[:60], description.strip()[:200], instructions.strip()[:2000], icon[:40], db.now()))
    return sid

def update(sid: str, name: str, description: str, instructions: str, icon: str):
    with db.get_conn() as conn:
        conn.execute("UPDATE skills SET name=?, description=?, instructions=?, icon=? WHERE id=?",
                     (name.strip()[:60], description.strip()[:200], instructions.strip()[:2000], icon[:40], sid))

def delete(sid: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM skills WHERE id=?", (sid,))
