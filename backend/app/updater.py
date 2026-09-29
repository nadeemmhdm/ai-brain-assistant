"""
GitHub-based updates.

Checking is automatic (a read-only call to the public GitHub API for the
latest release). Installing is one click, and only ever fast-forwards your
git checkout to a *release tag* of the official repository -- never an
arbitrary branch head -- and only when your working tree is clean.
"""
import os
import subprocess
import time
import httpx
from . import version, db
from .config import settings

REPO = "nadeemmhdm/ai-brain-assistant"
ROOT = version.ROOT
_cache: dict = {"at": 0, "data": None}

def _git(*args, timeout=60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)

def is_git_checkout() -> bool:
    return os.path.isdir(os.path.join(ROOT, ".git"))

def check(force: bool = False) -> dict:
    cur = version.current()
    if not force and _cache["data"] and time.time() - _cache["at"] < 1800:
        return {**_cache["data"], "current": cur}
    out = {"current": cur, "latest": None, "update_available": False, "notes": "", "url": None, "can_install": False, "error": None}
    try:
        r = httpx.get(f"https://api.github.com/repos/{REPO}/releases", timeout=10, headers={"Accept": "application/vnd.github+json", "User-Agent": "ai-brain-assistant"})
        r.raise_for_status()
        rels = [x for x in r.json() if not x.get("draft")]
        best = None
        for rel in rels:
            tag = rel["tag_name"]
            if version.parse(tag) and (best is None or version.parse(tag) > version.parse(best["tag_name"])):
                best = rel
        if best:
            out.update(latest=best["tag_name"].lstrip("v"), notes=(best.get("body") or "")[:1500], url=best["html_url"],
                       update_available=version.is_newer(best["tag_name"], cur))
    except Exception as e:
        out["error"] = f"Couldn't check for updates ({type(e).__name__}). Are you online?"
    out["can_install"] = out["update_available"] and is_git_checkout()
    _cache.update(at=time.time(), data=out)
    return out

def install() -> dict:
    info = check(force=True)
    if not info["update_available"]:
        return {"ok": True, "message": "Already up to date.", "restart_required": False}
    if not is_git_checkout():
        raise ValueError("This copy wasn't installed with git, so it can't update itself. Download the release from GitHub instead.")
    tag = "v" + info["latest"]
    if _git("status", "--porcelain").stdout.strip():
        raise ValueError("You have local changes, so I won't overwrite them. Commit or stash them first.")
    before = _git("rev-parse", "HEAD").stdout.strip()
    f = _git("fetch", "--tags", "--force", "origin", timeout=120)
    if f.returncode != 0:
        raise ValueError(f"git fetch failed: {f.stderr.strip()[:200]}")
    m = _git("merge", "--ff-only", tag)
    if m.returncode != 0:
        raise ValueError("Couldn't fast-forward to the release (your copy has diverged). Update manually with git.")
    changed = _git("diff", "--name-only", before, "HEAD").stdout.split()
    return {"ok": True, "message": f"Updated to {info['latest']}. Restart the app to use it.", "restart_required": True,
            "needs_pip": any(c.startswith("backend/requirements") for c in changed),
            "needs_npm": any(c in ("frontend/package.json", "frontend/package-lock.json") for c in changed)}
