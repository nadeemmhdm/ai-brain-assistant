from fastapi import APIRouter, HTTPException
import os, subprocess, sys, threading
from pydantic import BaseModel
from .. import translate

router = APIRouter(prefix="/api/translate", tags=["translate"])
_SETUP = {"status": "idle", "error": None}

@router.get("/status")
def status():
    return {"available": translate.available(), "installed": translate.installed_pairs(),
            "languages": translate.COMMON_LANGUAGES, "installing": translate.install_status()}

@router.get("/setup/status")
def setup_status():
    return _SETUP

@router.post("/setup")
def setup_engine():
    if _SETUP["status"] == "running":
        return _SETUP
    req = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "requirements-translate.txt"))
    _SETUP.update(status="running", error=None)
    def work():
        try:
            p = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req], capture_output=True, text=True, timeout=1800)
            if p.returncode:
                raise RuntimeError((p.stderr or p.stdout)[-1200:])
            _SETUP.update(status="completed", error=None)
        except Exception as e:
            _SETUP.update(status="failed", error=str(e)[:1200])
    threading.Thread(target=work, daemon=True).start()
    return _SETUP

@router.get("/catalog")
def catalog():
    return translate.catalog()

class InstallBody(BaseModel):
    from_code: str
    to_code: str

@router.post("/install")
def install(body: InstallBody):
    try:
        translate.install(body.from_code, body.to_code)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}

class TranslateBody(BaseModel):
    text: str
    from_code: str = "en"
    to_code: str

@router.post("")
def do_translate(body: TranslateBody):
    if not body.text.strip():
        raise HTTPException(400, "Nothing to translate.")
    try:
        return {"text": translate.translate(body.text, body.from_code, body.to_code)}
    except ValueError as e:
        raise HTTPException(400, str(e))
