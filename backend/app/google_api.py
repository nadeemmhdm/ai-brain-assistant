"""
Google integration (Gmail, Calendar/Meet, Sheets, Slides, Drive) through
YOUR OWN Google Cloud OAuth client. Nothing goes through any third party:
tokens are encrypted on disk (Fernet, key file in backend/data) and the
client secret only ever lives in backend/.env.

Safety rules baked in:
  * The language model never calls these functions. Every action is a
    button/form the user presses; email text is only ever summarised.
  * Anything destructive or visible to other people (send, trash, delete,
    invite) requires `confirm=True` from the UI's confirmation dialog.
  * "Delete" for mail means Trash (recoverable); permanent deletion would
    need Google's broadest mail scope, which we deliberately don't request.
"""
import base64
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlencode
import hashlib
import httpx
from .config import settings
from . import db

SCOPES = [
    "openid", "email",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
EMAIL_RE = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")

class GoogleError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message); self.status = status

_PENDING: dict[str, dict] = {}   # oauth state -> {verifier, expires}

def http() -> httpx.Client:      # indirection so tests can inject a mock transport
    return httpx.Client(timeout=20)

# ---------------------------------------------------------------- token storage
def _save_tokens(tok: dict):
    from . import vault
    try:
        vault.put("google_tokens", db.dumps(tok))
    except RuntimeError as e:
        raise GoogleError(str(e), 500)

def _load_tokens() -> dict | None:
    from . import vault
    try:
        raw = vault.get("google_tokens")
    except RuntimeError:
        return None
    return db.loads(raw) if raw else None

def configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)

def status() -> dict:
    tok = _load_tokens()
    return {"configured": configured(), "connected": bool(tok), "email": (tok or {}).get("email"),
            "redirect_uri": settings.google_redirect_uri}

# ---------------------------------------------------------------- OAuth (PKCE)
def auth_url() -> str:
    if not configured():
        raise GoogleError("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env first (see README → Google).")
    now = time.time()
    for k in [k for k, v in _PENDING.items() if v["expires"] < now]:
        _PENDING.pop(k)
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    _PENDING[state] = {"verifier": verifier, "expires": now + 600}
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    q = {"client_id": settings.google_client_id, "redirect_uri": settings.google_redirect_uri, "response_type": "code",
         "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
         "code_challenge": challenge, "code_challenge_method": "S256", "include_granted_scopes": "true"}
    return f"{AUTH_URL}?{urlencode(q)}"

def handle_callback(code: str, state: str):
    pend = _PENDING.pop(state, None)     # one-time use; also proves the flow was started from this app
    if not pend or pend["expires"] < time.time():
        raise GoogleError("Login expired or invalid. Start again from the app.")
    with http() as c:
        r = c.post(TOKEN_URL, data={"client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
                                    "code": code, "code_verifier": pend["verifier"], "grant_type": "authorization_code",
                                    "redirect_uri": settings.google_redirect_uri})
    if r.status_code != 200:
        raise GoogleError(f"Google refused the login: {r.json().get('error_description', r.text)[:200]}")
    j = r.json()
    email = None
    try:
        with http() as c:
            email = c.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {j['access_token']}"}).json().get("email")
    except Exception:
        pass
    _save_tokens({"access_token": j["access_token"], "refresh_token": j.get("refresh_token"),
                  "expires_at": time.time() + j.get("expires_in", 3600) - 60, "email": email})

def disconnect():
    tok = _load_tokens()
    if tok:
        try:
            with http() as c:
                c.post(REVOKE_URL, data={"token": tok.get("refresh_token") or tok["access_token"]})
        except Exception:
            pass
    from . import vault
    vault.delete("google_tokens")

def _access_token() -> str:
    tok = _load_tokens()
    if not tok:
        raise GoogleError("Google isn't connected. Connect it in the Google tab.", 401)
    if tok["expires_at"] > time.time():
        return tok["access_token"]
    if not tok.get("refresh_token"):
        raise GoogleError("Google session expired. Please reconnect.", 401)
    with http() as c:
        r = c.post(TOKEN_URL, data={"client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
                                    "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise GoogleError("Google session expired (apps in 'Testing' mode expire after 7 days). Please reconnect.", 401)
    j = r.json()
    tok.update(access_token=j["access_token"], expires_at=time.time() + j.get("expires_in", 3600) - 60)
    _save_tokens(tok)
    return tok["access_token"]

def call(method: str, url: str, **kw):
    with http() as c:
        r = c.request(method, url, headers={"Authorization": f"Bearer {_access_token()}"}, **kw)
    if r.status_code == 204 or not r.content:
        return {}
    if r.status_code >= 400:
        try: msg = r.json().get("error", {}).get("message", r.text)
        except Exception: msg = r.text
        raise GoogleError(f"Google API error ({r.status_code}): {msg[:250]}", 502 if r.status_code >= 500 else r.status_code)
    return r.json()

def need_confirm(confirm: bool, what: str):
    if not confirm:
        raise GoogleError(f"Confirmation required to {what}.", 409)

# ---------------------------------------------------------------- Gmail
GM = "https://gmail.googleapis.com/gmail/v1/users/me"

def _check_addrs(addrs: list[str]) -> list[str]:
    clean = [a.strip() for a in addrs if a.strip()]
    for a in clean:
        if not EMAIL_RE.match(a):
            raise GoogleError(f"'{a}' is not a valid email address.")
    return clean

def _raw(to, subject, body, cc=None) -> str:
    to = _check_addrs(to)
    if not to:
        raise GoogleError("Add at least one recipient.")
    m = EmailMessage()
    try:
        m["To"] = ", ".join(to)
        if cc:
            m["Cc"] = ", ".join(_check_addrs(cc))
        m["Subject"] = subject[:250]
    except ValueError:
        raise GoogleError("Subject/recipients contain invalid characters.")
    m.set_content(body)
    return base64.urlsafe_b64encode(m.as_bytes()).decode()

def _hdr(msg, name):
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""

def list_messages(q: str = "", max_results: int = 10) -> list[dict]:
    ids = call("GET", f"{GM}/messages", params={"q": q, "maxResults": min(max_results, 25)}).get("messages", [])
    out = []
    for m in ids:
        d = call("GET", f"{GM}/messages/{m['id']}", params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]})
        out.append({"id": d["id"], "thread_id": d.get("threadId"), "from": _hdr(d, "From"), "subject": _hdr(d, "Subject"),
                    "date": _hdr(d, "Date"), "snippet": d.get("snippet", ""), "unread": "UNREAD" in d.get("labelIds", [])})
    return out

def _body_text(payload) -> str:
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"] + "==").decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        t = _body_text(part)
        if t:
            return t
    return ""

def get_message(mid: str) -> dict:
    d = call("GET", f"{GM}/messages/{mid}", params={"format": "full"})
    return {"id": d["id"], "from": _hdr(d, "From"), "to": _hdr(d, "To"), "subject": _hdr(d, "Subject"),
            "date": _hdr(d, "Date"), "body": _body_text(d.get("payload", {}))[:8000]}

def create_draft(to, subject, body, cc=None) -> dict:
    d = call("POST", f"{GM}/drafts", json={"message": {"raw": _raw(to, subject, body, cc)}})
    return {"id": d["id"]}

def update_draft(did, to, subject, body, cc=None) -> dict:
    d = call("PUT", f"{GM}/drafts/{did}", json={"message": {"raw": _raw(to, subject, body, cc)}})
    return {"id": d["id"]}

def list_drafts() -> list[dict]:
    out = []
    for d in call("GET", f"{GM}/drafts", params={"maxResults": 15}).get("drafts", []):
        full = call("GET", f"{GM}/drafts/{d['id']}", params={"format": "metadata", "metadataHeaders": ["To", "Subject"]})
        msg = full.get("message", {})
        out.append({"id": d["id"], "to": _hdr(msg, "To"), "subject": _hdr(msg, "Subject"), "snippet": msg.get("snippet", "")})
    return out

def get_draft(did) -> dict:
    d = call("GET", f"{GM}/drafts/{did}", params={"format": "full"})
    msg = d.get("message", {})
    return {"id": did, "to": _hdr(msg, "To"), "cc": _hdr(msg, "Cc"), "subject": _hdr(msg, "Subject"), "body": _body_text(msg.get("payload", {}))}

def delete_draft(did, confirm):
    need_confirm(confirm, "delete this draft")
    call("DELETE", f"{GM}/drafts/{did}")

def send_draft(did, confirm) -> dict:
    need_confirm(confirm, "send this email")
    return {"id": call("POST", f"{GM}/drafts/send", json={"id": did}).get("id")}

def trash_message(mid, confirm):
    need_confirm(confirm, "move this email to Trash")
    call("POST", f"{GM}/messages/{mid}/trash")

# ---------------------------------------------------------------- Calendar / Meet
CAL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def create_meet(summary, start_iso=None, minutes=60, attendees=None, description="", confirm=False) -> dict:
    attendees = _check_addrs(attendees or [])
    if attendees:
        need_confirm(confirm, "invite these people (they'll receive an email)")
    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00")) if start_iso else datetime.now(timezone.utc)
    end = start + timedelta(minutes=max(5, min(minutes, 720)))
    body = {"summary": summary[:200] or "Meeting", "description": description[:2000],
            "start": {"dateTime": _iso(start), "timeZone": "UTC"}, "end": {"dateTime": _iso(end), "timeZone": "UTC"},
            "attendees": [{"email": a} for a in attendees],
            "conferenceData": {"createRequest": {"requestId": uuid.uuid4().hex, "conferenceSolutionKey": {"type": "hangoutsMeet"}}}}
    d = call("POST", CAL, params={"conferenceDataVersion": 1, "sendUpdates": "all" if attendees else "none"}, json=body)
    return _event(d)

def _event(d) -> dict:
    return {"id": d["id"], "summary": d.get("summary", ""), "start": d.get("start", {}).get("dateTime") or d.get("start", {}).get("date"),
            "end": d.get("end", {}).get("dateTime") or d.get("end", {}).get("date"), "meet_link": d.get("hangoutLink"),
            "html_link": d.get("htmlLink"), "attendees": [a["email"] for a in d.get("attendees", [])]}

def list_events(max_results=15) -> list[dict]:
    d = call("GET", CAL, params={"timeMin": _iso(datetime.now(timezone.utc)), "singleEvents": "true", "orderBy": "startTime", "maxResults": max_results})
    return [_event(e) for e in d.get("items", [])]

def update_event(eid, summary=None, start_iso=None, minutes=None, description=None) -> dict:
    patch = {}
    if summary is not None: patch["summary"] = summary[:200]
    if description is not None: patch["description"] = description[:2000]
    if start_iso:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        patch["start"] = {"dateTime": _iso(start), "timeZone": "UTC"}
        patch["end"] = {"dateTime": _iso(start + timedelta(minutes=minutes or 60)), "timeZone": "UTC"}
    return _event(call("PATCH", f"{CAL}/{eid}", params={"sendUpdates": "none"}, json=patch))

def share_meet(eid, emails, confirm) -> dict:
    emails = _check_addrs(emails)
    need_confirm(confirm, "invite these people (they'll receive an email)")
    cur = call("GET", f"{CAL}/{eid}")
    have = {a["email"] for a in cur.get("attendees", [])}
    merged = [{"email": e} for e in sorted(have | set(emails))]
    return _event(call("PATCH", f"{CAL}/{eid}", params={"sendUpdates": "all"}, json={"attendees": merged}))

def delete_event(eid, confirm):
    need_confirm(confirm, "delete this event (attendees will be notified)")
    call("DELETE", f"{CAL}/{eid}", params={"sendUpdates": "all"})

# ---------------------------------------------------------------- Sheets
SH = "https://sheets.googleapis.com/v4/spreadsheets"

def sheet_create(title) -> dict:
    d = call("POST", SH, json={"properties": {"title": title[:200] or "Untitled"}})
    return {"id": d["spreadsheetId"], "url": d["spreadsheetUrl"]}

def sheet_read(sid, rng="A1:Z50") -> dict:
    return {"values": call("GET", f"{SH}/{sid}/values/{rng}").get("values", [])}

def sheet_append(sid, rows, rng="A1") -> dict:
    return call("POST", f"{SH}/{sid}/values/{rng}:append", params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}, json={"values": rows})

def sheet_update(sid, rng, rows) -> dict:
    return call("PUT", f"{SH}/{sid}/values/{rng}", params={"valueInputOption": "USER_ENTERED"}, json={"values": rows})

# ---------------------------------------------------------------- Slides
SL = "https://slides.googleapis.com/v1/presentations"

def slides_create(title) -> dict:
    d = call("POST", SL, json={"title": title[:200] or "Untitled"})
    return {"id": d["presentationId"], "url": f"https://docs.google.com/presentation/d/{d['presentationId']}/edit"}

def slides_add(pid, title, body) -> dict:
    sid, tid, bid = (f"s{uuid.uuid4().hex[:12]}", f"t{uuid.uuid4().hex[:12]}", f"b{uuid.uuid4().hex[:12]}")
    reqs = [{"createSlide": {"objectId": sid, "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
                             "placeholderIdMappings": [{"layoutPlaceholder": {"type": "TITLE"}, "objectId": tid},
                                                       {"layoutPlaceholder": {"type": "BODY"}, "objectId": bid}]}},
            {"insertText": {"objectId": tid, "text": title[:200]}},
            {"insertText": {"objectId": bid, "text": body[:3000]}}]
    call("POST", f"{SL}/{pid}:batchUpdate", json={"requests": reqs})
    return {"slide_id": sid}

def slides_get(pid) -> dict:
    d = call("GET", f"{SL}/{pid}")
    return {"id": pid, "title": d.get("title"), "slides": len(d.get("slides", [])), "url": f"https://docs.google.com/presentation/d/{pid}/edit"}

# ---------------------------------------------------------------- Drive (files this app created)
def drive_list(kind: str = "all") -> list[dict]:
    mime = {"sheets": "application/vnd.google-apps.spreadsheet", "slides": "application/vnd.google-apps.presentation"}.get(kind)
    q = "trashed=false" + (f" and mimeType='{mime}'" if mime else "")
    d = call("GET", "https://www.googleapis.com/drive/v3/files", params={"q": q, "pageSize": 20, "orderBy": "modifiedTime desc",
                                                                        "fields": "files(id,name,mimeType,modifiedTime,webViewLink)"})
    return d.get("files", [])
