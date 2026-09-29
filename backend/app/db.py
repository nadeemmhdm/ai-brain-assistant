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

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,             -- a user-approved fact/preference
    embedding BLOB,
    created_at REAL NOT NULL,
    last_used_at REAL,
    use_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS downloads (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,                -- model|voice
    url TEXT NOT NULL,
    dest TEXT NOT NULL,
    status TEXT NOT NULL,              -- running|completed|failed|cancelled
    bytes_done INTEGER NOT NULL DEFAULT 0,
    bytes_total INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    started_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS mcp_servers (
    id TEXT PRIMARY KEY,
    key TEXT,                          -- catalog key if installed from the trusted list, else NULL
    name TEXT NOT NULL,
    command TEXT NOT NULL,             -- npm package (starts with @) or a local executable
    args_json TEXT,
    trusted INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    instructions TEXT NOT NULL,        -- folded into the system prompt for one message when invoked
    builtin INTEGER NOT NULL DEFAULT 0,
    icon TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    scope TEXT NOT NULL,               -- chat | always   ("this time" is never stored)
    conversation_id TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS autolearn_topics (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL UNIQUE,
    interval_hours INTEGER NOT NULL DEFAULT 168,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run REAL,
    last_status TEXT
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    topic TEXT,
    status TEXT NOT NULL DEFAULT 'draft',   -- draft|approved
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_items (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    instruction TEXT NOT NULL,
    input TEXT NOT NULL DEFAULT '',
    output TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 1,
    source_knowledge_id TEXT,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id)
);

CREATE TABLE IF NOT EXISTS training_jobs (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    base_model_path TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    hyperparams_json TEXT,
    status TEXT NOT NULL,             -- queued|running|completed|failed|cancelled
    progress_pct INTEGER NOT NULL DEFAULT 0,
    current_step TEXT,
    log_tail TEXT,
    error TEXT,
    started_at REAL NOT NULL,
    finished_at REAL
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
        # lightweight migrations for databases created by earlier versions
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        if "summary" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN summary TEXT")
        mcols = [r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
        if "action_json" not in mcols:
            conn.execute("ALTER TABLE messages ADD COLUMN action_json TEXT")
        if "confidence_json" not in mcols:
            conn.execute("ALTER TABLE messages ADD COLUMN confidence_json TEXT")
        if "summary_msgs" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN summary_msgs INTEGER NOT NULL DEFAULT 0")

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
