#!/usr/bin/env python3
"""
Starts the backend (uvicorn) and frontend (vite dev server) together, from
the repo root, and shuts both down cleanly on Ctrl+C.

    python scripts/run_dev.py

Assumes you've already run `pip install -r backend/requirements.txt` and
`npm install` in `frontend/` at least once (see the README). This does
NOT start your llama-server model processes -- those run independently
of this repo; start them first (see the README's Quick start).
"""
import os
import shutil
import subprocess
import sys
import threading
import time

from bootstrap import prepare

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")
IS_WINDOWS = os.name == "nt"

def _stream(proc: subprocess.Popen, prefix: str):
    for line in iter(proc.stdout.readline, b""):
        try:
            text = line.decode(errors="replace").rstrip()
        except Exception:
            text = str(line)
        print(f"[{prefix}] {text}")

def _npm_cmd() -> str:
    npm = shutil.which("npm.cmd") if IS_WINDOWS else shutil.which("npm")
    if not npm:
        print("npm not found on PATH. Install Node.js first: https://nodejs.org")
        sys.exit(1)
    return npm

def main():
    print("Starting AI Brain bootstrap...\n")
    try:
        python_exe, npm = prepare()
    except Exception as exc:
        print(f"Bootstrap failed: {exc}")
        sys.exit(1)
    python_exe = str(python_exe)
    print("\nStarting AI Brain (backend + frontend)... Ctrl+C to stop both.\n")

    backend = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    frontend = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=FRONTEND_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )

    threads = [
        threading.Thread(target=_stream, args=(backend, "backend "), daemon=True),
        threading.Thread(target=_stream, args=(frontend, "frontend"), daemon=True),
    ]
    for t in threads:
        t.start()

    try:
        while True:
            if backend.poll() is not None:
                print("\n[backend] exited unexpectedly -- stopping frontend too.")
                frontend.terminate()
                break
            if frontend.poll() is not None:
                print("\n[frontend] exited unexpectedly -- stopping backend too.")
                backend.terminate()
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        backend.terminate()
        frontend.terminate()
    finally:
        for p in (backend, frontend):
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
    print("Stopped.")

if __name__ == "__main__":
    main()
