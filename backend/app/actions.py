"""
Assistant actions + human permission.

The language model can only *propose* an action (it never runs one). Each
action needs the person's permission, chosen in the UI:

    Allow this time   -> runs once, nothing stored
    Allow this chat   -> remembered for this conversation only
    Always allow      -> remembered until revoked in Settings
    Deny              -> nothing happens

Grants are checked here on the server at execution time. Intent detection
looks only at what the USER typed -- never at email bodies, web pages or
other untrusted text -- so content in those can't trigger actions.
"""
import re
from datetime import datetime, timedelta, timezone
from . import db, google_api as g

# action -> (label, risk, needs)      risk: read | write | external | destructive
ACTIONS = {
    "gmail.read":    ("Read your recent emails", "read"),
    "gmail.draft":   ("Create an email draft", "write"),
    "gmail.send":    ("Send an email", "external"),
    "gmail.trash":   ("Move an email to Trash", "destructive"),
    "gmail.draft.delete": ("Delete a draft", "destructive"),
    "meet.create":   ("Create a Google Meet", "write"),
    "meet.invite":   ("Create a Meet and invite people (they get an email)", "external"),
    "meet.list":     ("Read your upcoming events", "read"),
    "meet.delete":   ("Delete a calendar event", "destructive"),
    "sheets.create": ("Create a Google Sheet", "write"),
    "sheets.write":  ("Write to a Google Sheet", "write"),
    "sheets.read":   ("Read a Google Sheet", "read"),
    "slides.create": ("Create a Google Slides deck", "write"),
    "slides.add":    ("Add slides to a deck", "write"),
    "gmail.get":     ("Open an email", "read"),
    "gmail.drafts":  ("List your drafts", "read"),
    "gmail.draft.get": ("Open a draft", "read"),
    "meet.update":   ("Edit a calendar event", "write"),
    "meet.share":    ("Invite people to an event (they get an email)", "external"),
    "drive.list":    ("List Sheets/Slides made with this app", "read"),
}

def describe(action: str) -> dict:
    label, risk = ACTIONS[action]
    return {"action": action, "label": label, "risk": risk}

# ------------------------------------------------------------- grants
def has_grant(action: str, conversation_id: str | None) -> bool:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM permissions WHERE action=? AND (scope='always' OR (scope='chat' AND conversation_id=?)) LIMIT 1",
            (action, conversation_id or "")).fetchone()
    return bool(row)

def add_grant(action: str, scope: str, conversation_id: str | None):
    if scope not in ("chat", "always"):
        return
    with db.get_conn() as conn:
        conn.execute("DELETE FROM permissions WHERE action=? AND scope=? AND COALESCE(conversation_id,'')=?", (action, scope, conversation_id or "" if scope == "chat" else ""))
        conn.execute("INSERT INTO permissions (id, action, scope, conversation_id, created_at) VALUES (?,?,?,?,?)",
                     (db.new_id(), action, scope, conversation_id if scope == "chat" else None, db.now()))

def list_grants() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT id, action, scope, conversation_id, created_at FROM permissions ORDER BY created_at DESC").fetchall()
    return [{**dict(r), "label": ACTIONS.get(r["action"], (r["action"],))[0]} for r in rows]

def revoke(grant_id: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM permissions WHERE id=?", (grant_id,))

# ------------------------------------------------------------- execution
def _emails(v):
    return [x.strip() for x in (v if isinstance(v, list) else str(v or "").replace(";", ",").split(",")) if x.strip()]

def run(action: str, p: dict) -> dict:
    """Execute (permission already verified by the caller)."""
    if action == "gmail.read":
        return {"messages": g.list_messages(str(p.get("q", ""))[:200], int(p.get("max", 8)))}
    if action == "gmail.draft":
        if p.get("draft_id"):
            return g.update_draft(p["draft_id"], _emails(p.get("to")), p.get("subject", ""), p.get("body", ""), _emails(p.get("cc")))
        return g.create_draft(_emails(p.get("to")), p.get("subject", ""), p.get("body", ""), _emails(p.get("cc")))
    if action == "gmail.send":
        d = g.create_draft(_emails(p.get("to")), p.get("subject", ""), p.get("body", ""), _emails(p.get("cc"))) if not p.get("draft_id") else {"id": p["draft_id"]}
        return g.send_draft(d["id"], True)
    if action == "gmail.trash":
        g.trash_message(p["id"], True); return {"ok": True}
    if action == "gmail.draft.delete":
        g.delete_draft(p["id"], True); return {"ok": True}
    if action in ("meet.create", "meet.invite"):
        att = _emails(p.get("attendees"))
        if att and action != "meet.invite":
            raise g.GoogleError("Inviting people needs the 'invite' permission.", 403)
        return g.create_meet(p.get("summary") or "Meeting", p.get("start"), int(p.get("minutes", 60)), att, p.get("description", ""), confirm=True)
    if action == "gmail.get":
        return g.get_message(p["id"])
    if action == "gmail.drafts":
        return {"drafts": g.list_drafts()}
    if action == "gmail.draft.get":
        return g.get_draft(p["id"])
    if action == "meet.update":
        return g.update_event(p["id"], p.get("summary"), p.get("start"), p.get("minutes"), p.get("description"))
    if action == "meet.share":
        return g.share_meet(p["id"], _emails(p.get("attendees")), True)
    if action == "drive.list":
        return {"files": g.drive_list(p.get("kind", "all"))}
    if action == "meet.list":
        return {"events": g.list_events()}
    if action == "meet.delete":
        g.delete_event(p["id"], True); return {"ok": True}
    if action == "sheets.create":
        r = g.sheet_create(p.get("title") or "Untitled")
        if p.get("rows"):
            g.sheet_append(r["id"], p["rows"])
        return r
    if action == "sheets.write":
        return g.sheet_append(p["id"], p["rows"], p.get("range", "A1")) if p.get("mode", "append") == "append" else g.sheet_update(p["id"], p["range"], p["rows"])
    if action == "sheets.read":
        return g.sheet_read(p["id"], p.get("range", "A1:Z50"))
    if action == "slides.create":
        r = g.slides_create(p.get("title") or "Untitled")
        for s in (p.get("slides") or [])[:8]:
            g.slides_add(r["id"], str(s.get("title", ""))[:200], str(s.get("body", ""))[:3000])
        return r
    if action == "slides.add":
        return g.slides_add(p["id"], p.get("title", ""), p.get("body", ""))
    raise g.GoogleError("Unknown action", 400)

# ------------------------------------------------------------- intent detection (user text only)
EMAIL = r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+"
_RE = {
    "read":   re.compile(r"\b(check|read|show|list|get|open|see)\b.{0,25}\b(my\s+)?(e-?mails?|inbox|mails?|messages)\b", re.I),
    "draft":  re.compile(r"\b(draft|write|compose|prepare)\b.{0,20}\b(an?\s+)?(e-?mail|mail)\b", re.I),
    "send":   re.compile(r"\b(send)\b.{0,20}\b(an?\s+)?(e-?mail|mail)\b", re.I),
    "meet":   re.compile(r"\b(create|make|schedule|set\s*up|start|book|new)\b.{0,25}\b(google\s+)?(meet|meeting|call|video\s*call)\b", re.I),
    "events": re.compile(r"\b(upcoming|next|my)\b.{0,20}\b(meetings?|events?|calendar|schedule)\b", re.I),
    "sheet":  re.compile(r"\b(create|make|new|start)\b.{0,20}\b(google\s+)?(sheets?|spreadsheet)\b", re.I),
    "slides": re.compile(r"\b(create|make|build|new|generate)\b.{0,20}\b(google\s+)?(slides?|presentation|slide\s*deck|deck|ppt)\b", re.I),
}

def _topic(text: str) -> str:
    m = re.search(r"\b(?:about|on|for|called|named|titled|regarding)\s+[\"“']?(.{3,100}?)[\"”']?(?:\s+(?:to|with|at|on|tomorrow|today|and)\b|[.?!]|$)", text, re.I)
    return (m.group(1).strip() if m else "").strip(" .,\"'")

def parse_when(text: str, tz_offset_min: int) -> str | None:
    """'tomorrow at 3pm' / 'today 17:30' / 'monday 10am' -> UTC ISO string (naive parsing, user's timezone)."""
    t = text.lower()
    m = re.search(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t[t.find("at "):] if "at " in t else t)
    day = None
    now_local = datetime.now(timezone.utc) - timedelta(minutes=tz_offset_min)
    if "tomorrow" in t: day = now_local.date() + timedelta(days=1)
    elif "today" in t or "tonight" in t: day = now_local.date()
    else:
        for i, wd in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            if wd in t:
                delta = (i - now_local.weekday()) % 7 or 7
                day = now_local.date() + timedelta(days=delta); break
    if not day or not m:
        return None
    hour, minute, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and hour < 12: hour += 12
    if ap == "am" and hour == 12: hour = 0
    if hour > 23 or minute > 59:
        return None
    local = datetime(day.year, day.month, day.day, hour, minute)
    return (local + timedelta(minutes=tz_offset_min)).replace(tzinfo=timezone.utc).isoformat()

def detect(text: str, tz_offset_min: int = 0) -> dict | None:
    """Returns {"action", "params", "needs_compose": bool} or None."""
    t = text.strip()
    if len(t) > 600 or "\n" in t[:2] :
        return None
    emails = re.findall(EMAIL, t)
    if _RE["send"].search(t) and emails:
        return {"action": "gmail.send", "params": {"to": emails, "instruction": t}, "needs_compose": "email"}
    if _RE["draft"].search(t):
        return {"action": "gmail.draft", "params": {"to": emails, "instruction": t}, "needs_compose": "email"}
    if _RE["read"].search(t):
        m = re.search(r"\bfrom\s+([\w.@+\-]+)", t, re.I)
        return {"action": "gmail.read", "params": {"q": f"from:{m.group(1)}" if m else "in:inbox", "max": 8}, "needs_compose": None}
    if _RE["events"].search(t) and not _RE["meet"].search(t):
        return {"action": "meet.list", "params": {}, "needs_compose": None}
    if _RE["meet"].search(t):
        p = {"summary": _topic(t) or "Meeting", "attendees": emails, "start": parse_when(t, tz_offset_min), "minutes": 60}
        dur = re.search(r"\b(\d{1,3})\s*(min|minutes|hour|hours|hr|hrs)\b", t, re.I)
        if dur:
            n = int(dur.group(1)); p["minutes"] = n * 60 if dur.group(2).lower().startswith(("hour", "hr")) else n
        return {"action": "meet.invite" if emails else "meet.create", "params": p, "needs_compose": None}
    if _RE["sheet"].search(t):
        return {"action": "sheets.create", "params": {"title": _topic(t) or "New sheet"}, "needs_compose": None}
    if _RE["slides"].search(t):
        return {"action": "slides.create", "params": {"title": _topic(t) or "New presentation", "instruction": t}, "needs_compose": "slides"}
    return None


def format_result(action: str, r: dict) -> str:
    if action == "gmail.read":
        ms = r.get("messages", [])
        if not ms: return "Your inbox has nothing matching that."
        return "Here are your latest emails:\n\n" + "\n".join(
            f"{i}. {'**' if m['unread'] else ''}{m['subject'] or '(no subject)'}{'**' if m['unread'] else ''} — {m['from'].split('<')[0].strip() or m['from']}\n   _{m['snippet'][:110]}_" for i, m in enumerate(ms, 1))
    if action in ("gmail.draft",): return "✅ Draft saved in your Gmail drafts. You can edit it in the **Google** tab or in Gmail."
    if action == "gmail.send": return "✅ Email sent."
    if action in ("gmail.trash", "gmail.draft.delete", "meet.delete"): return "✅ Done."
    if action in ("meet.create", "meet.invite"):
        link = r.get("meet_link")
        return (f"✅ Meeting **{r.get('summary')}** is set for {r.get('start')}.\n\n" + (f"Meet link: [{link}]({link})" if link else "") +
                (f"\n\nInvited: {', '.join(r.get('attendees', []))}" if r.get("attendees") else ""))
    if action == "meet.list":
        ev = r.get("events", [])
        if not ev: return "You have no upcoming events."
        return "Your upcoming events:\n\n" + "\n".join(f"- **{e['summary'] or '(no title)'}** — {e['start']}" + (f" · [Meet]({e['meet_link']})" if e.get("meet_link") else "") for e in ev)
    if action == "sheets.create": return f"✅ Created your sheet: [{r.get('url')}]({r.get('url')})"
    if action == "slides.create": return f"✅ Created your presentation: [{r.get('url')}]({r.get('url')})"
    return "✅ Done."
