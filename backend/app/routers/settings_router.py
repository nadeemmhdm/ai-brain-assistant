from fastapi import APIRouter
from pydantic import BaseModel
from .. import db
from ..config import settings as cfg

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULTS = {
    "reasoning_level": cfg.default_reasoning_level,
    "default_model": "main",
    "theme": "dark",
    "search_provider": "duckduckgo",
}

@router.get("")
def get_settings():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM kv_settings").fetchall()
    out = dict(DEFAULTS)
    out.update({r["key"]: r["value"] for r in rows})
    return out

class SettingBody(BaseModel):
    key: str
    value: str

@router.put("")
def set_setting(body: SettingBody):
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO kv_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (body.key, body.value),
        )
    return {"ok": True}
