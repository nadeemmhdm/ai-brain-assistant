"""
Tiny encrypted secret store (Fernet). Used for values the user types into
the UI once and that must never come back out: the Hugging Face token and
Google OAuth tokens. The key lives in backend/data/.secret_key (owner-only
permissions); ciphertext lives in the SQLite kv table. The API only ever
reports whether a secret is set -- it never returns the value.
"""
import os
from . import db
from .config import settings

def fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise RuntimeError("Install the 'cryptography' package (pip install -r requirements.txt) to store secrets securely.")
    path = os.path.join(settings.data_dir, ".secret_key")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(Fernet.generate_key())
        try: os.chmod(path, 0o600)
        except OSError: pass
    return Fernet(open(path, "rb").read())

def put(key: str, value: str):
    blob = fernet().encrypt(value.encode()).decode()
    with db.get_conn() as conn:
        conn.execute("INSERT INTO kv_settings (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f"vault:{key}", blob))

def get(key: str) -> str | None:
    with db.get_conn() as conn:
        row = conn.execute("SELECT value FROM kv_settings WHERE key=?", (f"vault:{key}",)).fetchone()
    if not row:
        return None
    try:
        return fernet().decrypt(row["value"].encode()).decode()
    except Exception:
        return None

def delete(key: str):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM kv_settings WHERE key=?", (f"vault:{key}",))

def has(key: str) -> bool:
    return get(key) is not None
