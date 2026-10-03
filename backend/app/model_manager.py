"""
Model manager: discover .gguf files, start/stop `llama-server` for the
main and agent roles, and talk to Hugging Face for search/downloads.

Only fixed, validated arguments are ever passed to llama-server -- nothing
from a model or a web page reaches a command line.
"""
import os
import shutil
import subprocess
from urllib.parse import urlparse
import httpx
from .config import settings
from . import downloads, db

PROCS: dict[str, dict] = {}

def _port(role: str) -> int:
    return urlparse(settings.main_model_url if role == "main" else settings.agent_model_url).port or (8081 if role == "main" else 8082)

def _imports() -> dict:
    with db.get_conn() as conn:
        row = conn.execute("SELECT value FROM kv_settings WHERE key='imported_models'").fetchone()
    return db.loads(row["value"]) if row else {}

def _save_imports(d: dict):
    with db.get_conn() as conn:
        conn.execute("INSERT INTO kv_settings (key,value) VALUES ('imported_models',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (db.dumps(d),))

def _role_key(role: str) -> str:
    if role not in ("main", "agent"):
        raise ValueError("role must be 'main' or 'agent'")
    return f"model_assignment_{role}"

def assignment(role: str) -> str | None:
    key=_role_key(role)
    with db.get_conn() as conn:
        row=conn.execute("SELECT value FROM kv_settings WHERE key=?",(key,)).fetchone()
    return row["value"] if row and row["value"] else None

def assignments() -> dict:
    return {"main": assignment("main"), "agent": assignment("agent")}

def set_assignment(role: str, filename: str) -> dict:
    _role_key(role)
    if os.path.basename(filename) != filename or not filename.lower().endswith(".gguf"):
        raise ValueError("Invalid model file name")
    if not resolve(filename):
        raise ValueError(f"{filename} is not available in your model library")
    with db.get_conn() as conn:
        conn.execute("INSERT INTO kv_settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (_role_key(role),filename))
    return {"role":role,"filename":filename}

def clear_assignment(role: str):
    key=_role_key(role)
    with db.get_conn() as conn:
        conn.execute("DELETE FROM kv_settings WHERE key=?",(key,))

def resolve(filename: str) -> str | None:
    """A model name -> its real path (models folder first, then imported-in-place)."""
    p = os.path.join(settings.models_dir, filename)
    if os.path.isfile(p):
        return p
    q = _imports().get(filename)
    return q if q and os.path.isfile(q) else None

def import_model(path: str, mode: str = "link") -> dict:
    """Bring in a .gguf you already downloaded somewhere else. `link` uses it where it is."""
    path = os.path.abspath(os.path.expanduser(path.strip().strip('"')))
    if not path.lower().endswith(".gguf"):
        raise ValueError("Only .gguf model files can be imported.")
    if not os.path.isfile(path):
        raise ValueError("I can't find that file. Check the path.")
    with open(path, "rb") as f:
        if f.read(4) != b"GGUF":
            raise ValueError("That file isn't a valid GGUF model.")
    name = os.path.basename(path)
    if mode == "copy":
        os.makedirs(settings.models_dir, exist_ok=True)
        dest = os.path.join(settings.models_dir, name)
        if os.path.exists(dest):
            raise ValueError(f"{name} is already in your models folder.")
        if os.path.getsize(path) > shutil.disk_usage(settings.models_dir).free:
            raise ValueError("Not enough free disk space to copy this model.")
        shutil.copy2(path, dest)
        return {"filename": name, "mode": "copy"}
    d = _imports(); d[name] = path; _save_imports(d)
    return {"filename": name, "mode": "link"}

def remove_import(filename: str):
    d = _imports(); d.pop(filename, None); _save_imports(d)

def list_local() -> list[dict]:
    seen, out = set(), []
    if os.path.isdir(settings.models_dir):
        for name in sorted(os.listdir(settings.models_dir)):
            if name.lower().endswith(".gguf"):
                p = os.path.join(settings.models_dir, name)
                out.append({"filename": name, "size_mb": round(os.path.getsize(p) / 1e6, 1), "imported": False}); seen.add(name)
    for name, p in _imports().items():
        if name not in seen and os.path.isfile(p):
            out.append({"filename": name, "size_mb": round(os.path.getsize(p) / 1e6, 1), "imported": True})
    return out

def running() -> dict:
    res = {}
    for role, info in list(PROCS.items()):
        if info["proc"].poll() is None:
            res[role] = {"filename": info["filename"], "port": info["port"]}
        else:
            PROCS.pop(role, None)
    return res

def load(role: str, filename: str) -> dict:
    if role not in ("main", "agent"):
        raise ValueError("role must be 'main' or 'agent'")
    if os.path.basename(filename) != filename or not filename.lower().endswith(".gguf"):
        raise ValueError("Invalid model file name")
    path = resolve(filename)
    if not path:
        raise ValueError(f"{filename} was not found in {settings.models_dir} or your imported models")
    set_assignment(role, filename)
    unload(role)
    port = _port(role)
    log = open(os.path.join(settings.data_dir, f"llama-{role}.log"), "ab")
    args = [settings.llama_server_path, "-m", path, "--host", "127.0.0.1", "--port", str(port),
            "-c", str(settings.llama_ctx), "-t", str(settings.llama_threads), "-ngl", str(settings.llama_gpu_layers)]
    try:
        proc = subprocess.Popen(args, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise ValueError("llama-server was not found. Install llama.cpp and set LLAMA_SERVER_PATH in backend/.env")
    PROCS[role] = {"proc": proc, "filename": filename, "port": port}
    return {"role": role, "filename": filename, "port": port}

def unload(role: str):
    info = PROCS.pop(role, None)
    if info and info["proc"].poll() is None:
        info["proc"].terminate()
        try:
            info["proc"].wait(timeout=8)
        except Exception:
            info["proc"].kill()

def restore_assignments() -> dict:
    """Start the user's persisted Main/Fast selections after app startup."""
    result = {}
    for role in ("main", "agent"):
        filename = assignment(role)
        if not filename:
            result[role] = {"status": "unassigned"}
            continue
        if not resolve(filename):
            result[role] = {"status": "missing", "filename": filename}
            continue
        try:
            load(role, filename)
            result[role] = {"status": "started", "filename": filename}
        except Exception as exc:
            result[role] = {"status": "failed", "filename": filename, "error": str(exc)}
    return result

def shutdown_all():
    for role in list(PROCS):
        unload(role)

# ---- Hugging Face ----------------------------------------------------------
def _hf_headers() -> dict:
    return downloads._headers()

def hf_search(query: str) -> list[dict]:
    r = httpx.get("https://huggingface.co/api/models", headers=_hf_headers(), timeout=15,
                  params={"search": query, "filter": "gguf", "sort": "downloads", "direction": -1, "limit": 20})
    r.raise_for_status()
    return [{"id": m["id"], "downloads": m.get("downloads", 0), "likes": m.get("likes", 0)} for m in r.json()]

def hf_files(repo: str) -> list[dict]:
    if not downloads.REPO_RE.match(repo):
        raise ValueError("Invalid repo id")
    r = httpx.get(f"https://huggingface.co/api/models/{repo}/tree/main", headers=_hf_headers(), timeout=15)
    r.raise_for_status()
    return [{"filename": f["path"], "size_mb": round((f.get("lfs", {}).get("size") or f.get("size", 0)) / 1e6, 1)}
            for f in r.json() if f.get("type") == "file" and f["path"].lower().endswith(".gguf") and "/" not in f["path"]]

def hf_download(repo: str, filename: str) -> str:
    url = downloads.hf_url(repo, filename)
    if not filename.lower().endswith(".gguf"):
        raise ValueError("Only .gguf model files can be downloaded here")
    return downloads.start("model", url, os.path.join(settings.models_dir, filename))
