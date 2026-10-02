"""
Optional local app-lock (section: "protect users' chat history and AI Brain").

Off by default -- the backend already only binds to 127.0.0.1, but on a
shared machine you may still want a passphrase between "anyone who opens
the browser" and your chat history / knowledge base. When a passphrase is
set, every /api/* route except /api/health and /api/auth/* requires a
valid session token.

No extra dependencies: passwords are hashed with PBKDF2-HMAC-SHA256
(stdlib `hashlib`), sessions are opaque random tokens (stdlib `secrets`)
held in memory and expire after SESSION_TTL_SECONDS or on backend restart.
"""
import hashlib
import hmac
import os
import secrets
import time
from fastapi import Header, HTTPException
from . import db

SESSION_TTL_SECONDS = 60 * 60 * 4  # 4 hours; local app-lock sessions are intentionally short-lived
_SESSIONS: dict[str, float] = {}  # token -> expires_at

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    iterations = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{salt.hex()}${iterations}${digest.hex()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, iterations, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except Exception:
        return False

def _get_hash() -> str | None:
    with db.get_conn() as conn:
        row = conn.execute("SELECT value FROM kv_settings WHERE key='auth_password_hash'").fetchone()
    return row["value"] if row else None

def is_configured() -> bool:
    return _get_hash() is not None

def setup_password(password: str):
    if is_configured():
        raise HTTPException(400, "A passphrase is already set. Use change_password instead.")
    if len(password) < 4:
        raise HTTPException(400, "Passphrase must be at least 4 characters.")
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO kv_settings (key, value) VALUES ('auth_password_hash', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (_hash_password(password),),
        )

def change_password(current: str, new: str):
    stored = _get_hash()
    if not stored or not _verify_password(current, stored):
        raise HTTPException(401, "Current passphrase is incorrect.")
    if len(new) < 4:
        raise HTTPException(400, "New passphrase must be at least 4 characters.")
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE kv_settings SET value=? WHERE key='auth_password_hash'",
            (_hash_password(new),),
        )
    _SESSIONS.clear()  # invalidate existing sessions on password change

def remove_password(current: str):
    stored = _get_hash()
    if not stored or not _verify_password(current, stored):
        raise HTTPException(401, "Current passphrase is incorrect.")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM kv_settings WHERE key='auth_password_hash'")
    _SESSIONS.clear()

def login(password: str) -> str:
    stored = _get_hash()
    if not stored or not _verify_password(password, stored):
        raise HTTPException(401, "Incorrect passphrase.")
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = time.time() + SESSION_TTL_SECONDS
    return token

def logout(token: str):
    _SESSIONS.pop(token, None)

def _session_valid(token: str) -> bool:
    exp = _SESSIONS.get(token)
    if exp is None:
        return False
    if exp < time.time():
        _SESSIONS.pop(token, None)
        return False
    return True

async def require_auth(authorization: str | None = Header(default=None)):
    """FastAPI dependency: enforced on protected routers. No-op (allows
    the request through) if no passphrase has ever been configured, so
    the app keeps working unauthenticated by default."""
    if not is_configured():
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing session token.")
    token = authorization[len("Bearer "):]
    if not _session_valid(token):
        raise HTTPException(401, "Session expired or invalid. Please log in again.")
