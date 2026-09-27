"""
SQLite persistence. One file, zero setup. Holds:
  - conversations / messages  (chat history, auto-saved, supports fork/edit/delete)
  - knowledge / sources       (the "AI Brain")
  - learning_sessions         (Auto Learn history)
  - kv_settings               (user settings, e.g. reasoning level, theme, model)
"""
import sqlite3
import json
import time
import uuid
import os
from contextlib import contextmanager
from .config import settings

DB_PATH = os.path.join(settings.data_dir, "brain.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    parent_id TEXT,
    role TEXT NOT NULL,               -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    thinking TEXT,                    -- optional <thinking> scratchpad
    sources_json TEXT,                -- JSON list of source dicts, if search mode used
    model TEXT,
    reasoning_level TEXT,
    created_at REAL NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    source_type TEXT,                 -- gov/edu/official/community/forum/...
    trust_tier TEXT,                  -- A/B/C/D
    fetched_at REAL NOT NULL,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    topic TEXT,
    subtopic TEXT,
    question TEXT,
    answer TEXT,
    summary TEXT,
    embedding BLOB,
    source_ids_json TEXT,
    verification_status TEXT,          -- 'unverified'|'verified'|'conflict'
    conflict_json TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_sessions (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT NOT NULL,              -- running|paused|completed|cancelled|error
    stats_json TEXT,
    started_at REAL NOT NULL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS kv_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_cache (
    query TEXT PRIMARY KEY,
    provider TEXT,
    results_json TEXT,
    fetched_at REAL NOT NULL
);
"""

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)

@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def new_id() -> str:
    return uuid.uuid4().hex

def now() -> float:
    return time.time()

def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

def loads(s):
    if not s:
        return None
    return json.loads(s)
