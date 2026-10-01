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
    {"name": "Translate", "icon": "Languages", "description": "Real offline translation (Argos Translate) — say 'to <language>: <text>'.",
     "instructions": "", "kind": "translate"},
    {"name": "Brainstorm", "icon": "Sparkles", "description": "Generate varied, concrete ideas.",
     "instructions": "Brainstorm a set of varied, concrete ideas for the user's request. Prefer specific, actionable ideas over vague ones, and briefly note the trade-off of each."},
    {"name": "Code review", "icon": "Code2", "description": "Review code for bugs, clarity and style.",
     "instructions": "Review the given code like a careful, friendly senior engineer: point out real bugs or edge cases first, then readability/style issues, then optional nice-to-haves. Be specific (line/function) and concise; don't rewrite the whole thing unless asked."},
    {"name": "Make concise", "icon": "Scissors", "description": "Shorten text while keeping the meaning.",
     "instructions": "Rewrite the user's text to be noticeably shorter and tighter, cutting filler and redundancy, while keeping every fact and the original meaning and tone intact. Return only the rewritten text."},
    {"name": "Debug this", "icon": "Bug", "description": "Diagnose an error message or unexpected behavior.",
     "instructions": "The user will paste an error message, stack trace, or a description of unexpected behavior, usually with some code. Identify the most likely root cause first, explain briefly why it happens, then give a concrete fix. If you need more information to be sure, say what's missing and give your best guess in the meantime."},
    {"name": "Action items", "icon": "ListChecks", "description": "Turn notes or a transcript into action items.",
     "instructions": "Read the user's notes or meeting transcript and extract a clean list of action items, each as '- [ ] Task — owner (if mentioned) — due date (if mentioned)'. Then list any open questions or decisions that still need to be made. Don't invent owners or dates that weren't stated."},
    {"name": "Pros and cons", "icon": "Scale", "description": "Lay out a balanced pros/cons comparison.",
     "instructions": "Lay out a clear, balanced 'Pros' and 'Cons' list for the user's decision or option. Be evenhanded -- don't stack one side to nudge a conclusion. End with one short sentence naming what the choice most depends on, without telling the user what to pick unless they ask."},
    {"name": "Mock interviewer", "icon": "Mic", "description": "Practice interview questions, one at a time.",
     "instructions": "Act as an interviewer for the role or topic the user names. Ask one realistic question at a time and wait for their answer before the next one. After each answer, give brief, specific, encouraging feedback (what was strong, one thing to improve) before the next question."},
    {"name": "Write tests", "icon": "FlaskConical", "description": "Write unit tests for the given code.",
     "instructions": "Write clear, focused unit tests for the user's code: cover the normal case, the obvious edge cases, and at least one failure case. Match the testing framework/style already used in the code if shown; otherwise pick a sensible common one for the language and say which you picked."},
]

def seed():
    with db.get_conn() as conn:
        have = {r["name"] for r in conn.execute("SELECT name FROM skills WHERE builtin=1").fetchall()}
        for b in BUILTINS:
            if b["name"] not in have:
                conn.execute("INSERT INTO skills (id, name, description, instructions, kind, builtin, icon, created_at) VALUES (?,?,?,?,?,1,?,?)",
                             (db.new_id(), b["name"], b["description"], b["instructions"], b.get("kind", "prompt"), b["icon"], db.now()))

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
        conn.execute("INSERT INTO skills (id, name, description, instructions, kind, builtin, icon, created_at) VALUES (?,?,?,?,'prompt',0,?,?)",
                     (sid, name.strip()[:60], description.strip()[:200], instructions.strip()[:2000], icon[:40], db.now()))
    return sid

def update(sid: str, name: str, description: str, instructions: str, icon: str):
    with db.get_conn() as conn:
        conn.execute("UPDATE skills SET name=?, description=?, instructions=?, icon=? WHERE id=?",
                     (name.strip()[:60], description.strip()[:200], instructions.strip()[:2000], icon[:40], sid))

def delete(sid: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM skills WHERE id=?", (sid,))
