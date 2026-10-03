"""Optional local app-lock for protecting local chats and Brain data."""
import hashlib
import hmac
import os
import secrets
import time
from fastapi import Header, HTTPException
from . import db

SESSION_TTL_SECONDS = 60 * 60 * 4
MIN_PASSPHRASE_LENGTH = 10
MAX_FAILED_LOGINS = 8
LOGIN_WINDOW_SECONDS = 60
_FAILED_LOGINS: list[float] = []
_SESSIONS: dict[str, float] = {}

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
        row = conn.execute("SELECT value FROM kv_settings WHERE key=?", ("auth_password_hash",)).fetchone()
    return row["value"] if row else None

def is_configured() -> bool:
    return _get_hash() is not None

def _validate_new_password(password: str) -> None:
    if len(password) < MIN_PASSPHRASE_LENGTH:
        raise HTTPException(400, f"Passphrase must be at least {MIN_PASSPHRASE_LENGTH} characters.")

def setup_password(password: str):
    if is_configured():
        raise HTTPException(400, "A passphrase is already set. Use change_password instead.")
    _validate_new_password(password)
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO kv_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("auth_password_hash", _hash_password(password)),
        )

def change_password(current: str, new: str):
    stored = _get_hash()
    if not stored or not _verify_password(current, stored):
        raise HTTPException(401, "Current passphrase is incorrect.")
    _validate_new_password(new)
    with db.get_conn() as conn:
        conn.execute("UPDATE kv_settings SET value=? WHERE key=?", (_hash_password(new), "auth_password_hash"))
    _SESSIONS.clear()

def remove_password(current: str):
    stored = _get_hash()
    if not stored or not _verify_password(current, stored):
        raise HTTPException(401, "Current passphrase is incorrect.")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM kv_settings WHERE key=?", ("auth_password_hash",))
    _SESSIONS.clear()
    _FAILED_LOGINS.clear()

def login(password: str) -> str:
    now = time.time()
    _FAILED_LOGINS[:] = [t for t in _FAILED_LOGINS if now - t < LOGIN_WINDOW_SECONDS]
    if len(_FAILED_LOGINS) >= MAX_FAILED_LOGINS:
        raise HTTPException(429, "Too many failed login attempts. Try again shortly.")
    stored = _get_hash()
    if not stored or not _verify_password(password, stored):
        _FAILED_LOGINS.append(now)
        raise HTTPException(401, "Incorrect passphrase.")
    _FAILED_LOGINS.clear()
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = now + SESSION_TTL_SECONDS
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
    if not is_configured():
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing session token.")
    token = authorization[len("Bearer "):]
    if not _session_valid(token):
        raise HTTPException(401, "Session expired or invalid. Please log in again.")
