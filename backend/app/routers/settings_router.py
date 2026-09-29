from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import db
from ..config import settings as cfg

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Only these keys can be read or written through the API. Secrets that
# live in the same table (e.g. the passphrase hash, Google tokens) are
# deliberately NOT exposed here.
DEFAULTS = {
    "reasoning_level": cfg.default_reasoning_level,
    "default_model": "main",
    "theme": "dark",
    "search_provider": "duckduckgo",
    "search_mode": "quick",          # off | quick | deep
    "ai_name": "Nila",
    "user_name": "",
    "onboarded": "false",
    "wake_word_enabled": "false",
    "voice_engine": "auto",          # auto | local | browser
    "tts_voice": "",
    "speak_replies": "true",
    "remember_research": "true",
    "check_updates": "true",
    "auto_install_updates": "false",   # off by default: installs only official release tags, at startup
    "sidebar_open": "true",
}

@router.get("")
def get_settings():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM kv_settings").fetchall()
    out = dict(DEFAULTS)
    out.update({r["key"]: r["value"] for r in rows if r["key"] in DEFAULTS})
    return out

class SettingBody(BaseModel):
    key: str
    value: str

@router.put("")
def set_setting(body: SettingBody):
    if body.key not in DEFAULTS:
        raise HTTPException(400, f"Unknown or protected setting: {body.key}")
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO kv_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (body.key, body.value[:500]),
        )
    return {"ok": True}

def get_value(key: str) -> str:
    with db.get_conn() as conn:
        row = conn.execute("SELECT value FROM kv_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULTS.get(key, "")
