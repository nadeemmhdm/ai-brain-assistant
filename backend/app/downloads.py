"""
Background file downloads (Hugging Face models and voice files).

Internet is only needed for these downloads; once a file is on disk the
app never needs the network to use it. Downloads are resumable (`.part`
file + HTTP Range), restricted to huggingface.co, and the optional
HF_TOKEN stays on the backend (httpx drops it on cross-host redirects).
"""
import os
import re
import shutil
import threading
from urllib.parse import urlparse
import httpx
from . import db
from .config import settings

ALLOWED_HOSTS = {"huggingface.co"}
_CANCEL: set[str] = set()

REPO_RE = re.compile(r"^[A-Za-z0-9][\w.\-]{0,95}/[A-Za-z0-9][\w.\-]{0,95}$")
FILE_RE = re.compile(r"^[\w][\w.\-]{0,200}$")  # a bare file name; no slashes -> no path traversal

def hf_url(repo: str, filename: str, subpath: str = "") -> str:
    if not REPO_RE.match(repo):
        raise ValueError("Invalid Hugging Face repo id")
    for part in filter(None, subpath.split("/")):
        if not FILE_RE.match(part):
            raise ValueError("Invalid path")
    if not FILE_RE.match(filename):
        raise ValueError("Invalid file name")
    path = f"{subpath.strip('/')}/{filename}" if subpath else filename
    return f"https://huggingface.co/{repo}/resolve/main/{path}"

def hf_token() -> str:
    from . import vault
    try:
        return vault.get("hf_token") or settings.hf_token
    except RuntimeError:
        return settings.hf_token

def _headers() -> dict:
    h = {"User-Agent": "ai-brain-assistant"}
    t = hf_token()
    if t:
        h["Authorization"] = f"Bearer {t}"   # only ever sent to huggingface.co
    return h

def _worker(did: str, url: str, dest: str):
    part = dest + ".part"
    try:
        done = os.path.getsize(part) if os.path.exists(part) else 0
        headers = _headers()
        if done:
            headers["Range"] = f"bytes={done}-"
        with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=30) as r:
            if r.status_code == 416:      # already complete
                os.replace(part, dest)
                _finish(did, "completed", done, done); return
            if r.status_code not in (200, 206):
                raise RuntimeError(f"Server answered {r.status_code}. (Private/gated repos need HF_TOKEN in backend/.env)")
            if r.status_code == 200:
                done = 0
            total = done + int(r.headers.get("content-length", 0))
            free = shutil.disk_usage(os.path.dirname(dest)).free
            if total and total - done > free:
                raise RuntimeError("Not enough free disk space for this download.")
            with open(part, "ab" if done else "wb") as f:
                for chunk in r.iter_bytes(1024 * 256):
                    if did in _CANCEL:
                        _CANCEL.discard(did)
                        _finish(did, "cancelled", done, total); return
                    f.write(chunk); done += len(chunk)
                    with db.get_conn() as conn:
                        conn.execute("UPDATE downloads SET bytes_done=?, bytes_total=? WHERE id=?", (done, total, did))
        os.replace(part, dest)
        _finish(did, "completed", done, total)
    except Exception as e:
        _finish(did, "failed", 0, 0, str(e)[:300])

def _finish(did, status, done, total, error=None):
    with db.get_conn() as conn:
        conn.execute("UPDATE downloads SET status=?, bytes_done=?, bytes_total=?, error=? WHERE id=?", (status, done, total, error, did))

def start(kind: str, url: str, dest: str) -> str:
    if urlparse(url).hostname not in ALLOWED_HOSTS or urlparse(url).scheme != "https":
        raise ValueError("Only https://huggingface.co downloads are allowed.")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        raise ValueError("That file is already downloaded.")
    did = db.new_id()
    with db.get_conn() as conn:
        conn.execute("INSERT INTO downloads (id, kind, url, dest, status, started_at) VALUES (?,?,?,?,?,?)",
                     (did, kind, url, dest, "running", db.now()))
    threading.Thread(target=_worker, args=(did, url, dest), daemon=True).start()
    return did

def cancel(did: str):
    _CANCEL.add(did)

def list_downloads(kind: str | None = None) -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM downloads " + ("WHERE kind=? " if kind else "") + "ORDER BY started_at DESC LIMIT 30",
                            (kind,) if kind else ()).fetchall()
    return [{**dict(r), "name": os.path.basename(r["dest"])} for r in rows]
