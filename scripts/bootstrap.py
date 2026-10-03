#!/usr/bin/env python3
"""AI Brain bootstrap: repair dependencies, check releases, then launch safely.

Uses only the Python standard library so it can run before backend dependencies
exist. It never overwrites a dirty git checkout and only updates to published
release tags from the official repository.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
STATE = ROOT / ".bootstrap-state.json"
REPO = "nadeemmhdm/ai-brain-assistant"
API = f"https://api.github.com/repos/{REPO}"
IS_WINDOWS = os.name == "nt"
MIN_PYTHON = (3, 10)
MIN_NODE_MAJOR = 18


def run(cmd, *, cwd=ROOT, check=False, timeout=300):
    return subprocess.run(
        [str(x) for x in cmd], cwd=str(cwd), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=check, timeout=timeout,
    )


def command(name: str):
    if IS_WINDOWS and name in {"npm", "node", "git"}:
        return shutil.which(name + ".cmd") or shutil.which(name + ".exe") or shutil.which(name)
    return shutil.which(name)


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    try:
        STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def digest(*paths: Path):
    h = hashlib.sha256()
    for path in paths:
        if path.exists():
            h.update(path.read_bytes())
    return h.hexdigest()


def version_key(value: str):
    import re
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-([A-Za-z]+)\.(\d+))?", value.strip())
    if not m:
        return None
    major, minor, patch, pre_name, pre_num = m.groups()
    # finals sort above prereleases of the same base version
    return (int(major), int(minor), int(patch), pre_name is None, int(pre_num or 0))


def current_version():
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def github_json(path: str):
    req = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ai-brain-assistant-bootstrap"},
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.load(response)


def check_and_install_app_update():
    """Update a clean git checkout to the newest published release tag."""
    print(f"[update] AI Brain {current_version()} — checking GitHub Releases...")
    try:
        releases = github_json("/releases?per_page=30")
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"[update] Offline/unavailable; continuing with installed version ({type(exc).__name__}).")
        return False

    candidates = [r for r in releases if not r.get("draft") and version_key(r.get("tag_name", ""))]
    if not candidates:
        print("[update] No published release found; continuing.")
        return False
    latest = max(candidates, key=lambda r: version_key(r["tag_name"]))
    latest_tag = latest["tag_name"]
    if not version_key(latest_tag) > (version_key(current_version()) or (0, 0, 0, False, 0)):
        print("[update] Application is up to date.")
        return False

    print(f"[update] New release available: {latest_tag}")
    git = command("git")
    if not git or not (ROOT / ".git").is_dir():
        print("[update] Auto-install skipped: this copy is not a git checkout (or git is unavailable).")
        return False
    dirty = run([git, "status", "--porcelain", "--untracked-files=all"]).stdout.strip()
    stash_created = False
    stash_ref = None
    if dirty:
        changed = [line[3:] if len(line) > 3 else line for line in dirty.splitlines()]
        preview = ", ".join(changed[:4]) + ("…" if len(changed) > 4 else "")
        print(f"[update] Local changes detected ({preview}). Preserving them before update…")
        # Never delete or reset user work. Stash tracked + untracked files, update the
        # release, then restore them. This also handles generated lockfile noise.
        stashed = run([git, "stash", "push", "--include-untracked", "-m",
                       f"AI Brain auto-update backup before {latest_tag}"], timeout=120)
        if stashed.returncode:
            print("[update] Could not safely back up local changes; update skipped. Nothing was overwritten.")
            return False
        stash_created = "No local changes to save" not in stashed.stdout
        if stash_created:
            stash_ref = run([git, "rev-parse", "stash@{0}"]).stdout.strip() or None
            print("[update] Local changes backed up safely.")

    before = run([git, "rev-parse", "HEAD"]).stdout.strip()
    fetched = run([git, "fetch", "--tags", "--force", "origin"], timeout=120)
    if fetched.returncode:
        print("[update] git fetch failed; continuing with installed version.")
        if stash_created:
            restored = run([git, "stash", "pop"], timeout=120)
            if restored.returncode:
                print("[update] Your local-change backup remains in git stash; it was not deleted.")
            else:
                print("[update] Local changes restored.")
        return False
    merged = run([git, "merge", "--ff-only", latest_tag], timeout=120)
    if merged.returncode:
        print("[update] Release cannot be fast-forwarded safely; continuing without modifying release files.")
        if stash_created:
            restored = run([git, "stash", "pop"], timeout=120)
            if restored.returncode:
                print("[update] Your local-change backup remains in git stash; it was not deleted.")
        return False

    after = run([git, "rev-parse", "HEAD"]).stdout.strip()
    if stash_created:
        restored = run([git, "stash", "pop"], timeout=120)
        if restored.returncode:
            print("[update] Updated, but local changes overlap the new release.")
            print("[update] Your backup is preserved in git stash; resolve the overlap manually.")
        else:
            print("[update] Local changes restored after the release update.")
    if before != after:
        print(f"[update] Updated successfully to {latest_tag}.")
        return True
    return False


def ensure_python():
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required; "
            f"current is {sys.version_info.major}.{sys.version_info.minor}."
        )
    print(f"[check] Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}: OK")


def venv_python():
    return BACKEND / ".venv" / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def ensure_backend(state, force=False):
    py = venv_python()
    if not py.exists():
        print("[install] Creating backend virtual environment...")
        run([sys.executable, "-m", "venv", str(BACKEND / ".venv")], check=True, timeout=180)

    req = BACKEND / "requirements.txt"
    req_hash = digest(req)
    needs = force or state.get("backend_requirements") != req_hash
    probe = run([str(py), "-c", "import fastapi,uvicorn,httpx,pydantic,ddgs,trafilatura,bs4,numpy,dotenv,cryptography"])
    if probe.returncode:
        needs = True
    if needs:
        print("[install] Installing/repairing backend packages...")
        run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True, timeout=300)
        # --upgrade keeps packages current while requirements.txt version ranges
        # remain the compatibility boundary.
        run([str(py), "-m", "pip", "install", "--upgrade", "-r", str(req)], check=True, timeout=900)
        state["backend_requirements"] = req_hash
    else:
        print("[check] Backend packages: OK")
    return py


def try_install_node_windows():
    winget = command("winget")
    if not winget:
        return False
    print("[install] Node.js missing/outdated; requesting Node.js LTS via winget...")
    result = run(
        [winget, "install", "--id", "OpenJS.NodeJS.LTS", "-e",
         "--accept-package-agreements", "--accept-source-agreements"],
        timeout=900,
    )
    return result.returncode == 0


def node_major(node):
    try:
        out = run([node, "--version"], timeout=15).stdout.strip().lstrip("v")
        return int(out.split(".", 1)[0]), out
    except Exception:
        return 0, "unknown"


def ensure_node():
    node = command("node")
    major, full = node_major(node) if node else (0, "missing")
    if major < MIN_NODE_MAJOR and IS_WINDOWS:
        try_install_node_windows()
        node = command("node")
        major, full = node_major(node) if node else (0, "missing")
    if major < MIN_NODE_MAJOR:
        raise SystemExit(f"Node.js {MIN_NODE_MAJOR}+ is required (found {full}). Install Node.js LTS and run again.")
    npm = command("npm")
    if not npm:
        raise SystemExit("npm is unavailable even though Node.js was found.")
    print(f"[check] Node.js {full}: OK")
    return npm


def ensure_frontend(state, npm, force=False):
    lock = FRONTEND / "package-lock.json"
    package = FRONTEND / "package.json"
    dep_hash = digest(package, lock)
    node_modules = FRONTEND / "node_modules"
    needs = force or not node_modules.is_dir() or state.get("frontend_dependencies") != dep_hash
    if needs:
        print("[install] Installing/repairing frontend packages from lockfile...")
        # npm ci gives a reproducible dependency tree and avoids silently
        # drifting to incompatible package versions.
        result = run([npm, "ci"], cwd=FRONTEND, timeout=900)
        if result.returncode:
            print("[install] npm ci failed; trying npm install as recovery...")
            run([npm, "install"], cwd=FRONTEND, check=True, timeout=900)
        state["frontend_dependencies"] = dep_hash
    else:
        print("[check] Frontend packages: OK")


def prepare():
    ensure_python()
    app_updated = check_and_install_app_update()
    state = load_state()
    py = ensure_backend(state, force=app_updated)
    # Release-integrity preflight: catch router/import mismatches before spawning
    # backend + frontend processes, with an actionable error instead of a long
    # uvicorn traceback.
    smoke = run([str(py), "-c", "import main; from app import teacher_mode; from app.routers import teacher_router; assert callable(teacher_mode.curriculum); assert teacher_router.Curriculum(topic='smoke').topic == 'smoke'"], cwd=BACKEND, timeout=60)
    if smoke.returncode:
        detail = (smoke.stderr or smoke.stdout or "").strip()
        raise RuntimeError("Backend release-integrity check failed. " + detail[-1200:])
    print("[check] Backend startup imports: OK")
    npm = ensure_node()
    ensure_frontend(state, npm, force=app_updated)
    save_state(state)
    return py, npm


if __name__ == "__main__":
    try:
        prepare()
        print("\nAI Brain is installed and ready.")
        print("Run: python scripts/run_dev.py")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        print(f"\nSetup failed (exit {exc.returncode}). {detail[-800:]}", file=sys.stderr)
        raise SystemExit(exc.returncode or 1)
