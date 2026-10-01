"""
A real (small) MCP client, stdio transport -- the standard way official
Anthropic reference servers run locally. Not a stub: this spawns the
server process, speaks JSON-RPC 2.0 over its stdin/stdout, and can list
and call real tools.

Trusted starter catalog: the official servers published under
@modelcontextprotocol on npm (github.com/modelcontextprotocol/servers),
picked for needing no extra API keys/credentials:

  filesystem            read/write files in ONE folder you choose (sandboxed to it)
  fetch                 fetch and clean up a web page
  git                   read/inspect a local git repository
  sequential-thinking   a structured scratchpad the model can use for hard problems

Anything else can be added manually (Settings -> MCP -> Add custom), but
only these ship pre-listed as "trusted" -- and every one still needs the
user's explicit Install, same as the Google/Gmail actions.
"""
import asyncio
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from . import db
from .config import settings

CATALOG = [
    {"key": "filesystem", "name": "Filesystem", "package": "@modelcontextprotocol/server-filesystem",
     "description": "Read and write files in one folder you choose. The server can only see that folder.",
     "needs_path": True, "risk": "write"},
    {"key": "fetch", "name": "Web Fetch", "package": "@modelcontextprotocol/server-fetch",
     "description": "Fetch a web page and return clean, readable text.", "needs_path": False, "risk": "read"},
    {"key": "git", "name": "Git", "package": "@modelcontextprotocol/server-git",
     "description": "Read history, diffs and status of a local git repository (read-only).",
     "needs_path": True, "risk": "read"},
    {"key": "sequential-thinking", "name": "Sequential Thinking", "package": "@modelcontextprotocol/server-sequential-thinking",
     "description": "A structured scratchpad tool the model can use to reason through hard, multi-step problems.",
     "needs_path": False, "risk": "read"},
    {"key": "memory", "name": "Memory (knowledge graph)", "package": "@modelcontextprotocol/server-memory",
     "description": "A simple local knowledge graph the model can save entities and relations to across a session.",
     "needs_path": False, "risk": "write"},
    {"key": "time", "name": "Time", "package": "@modelcontextprotocol/server-time",
     "description": "Current time and date conversions between timezones -- no internet needed.",
     "needs_path": False, "risk": "read"},
    {"key": "sqlite", "name": "SQLite", "package": "@modelcontextprotocol/server-sqlite",
     "description": "Query and inspect a local SQLite database file you choose (read/write to that one file).",
     "needs_path": True, "risk": "write"},
    {"key": "everything", "name": "Everything (demo/test)", "package": "@modelcontextprotocol/server-everything",
     "description": "The official reference/test server -- exercises every MCP feature. Useful to confirm MCP itself is working.",
     "needs_path": False, "risk": "read"},
]
CATALOG_BY_KEY = {c["key"]: c for c in CATALOG}

@dataclass
class ServerHandle:
    proc: object
    tools: list = field(default_factory=list)
    lock: object = field(default_factory=asyncio.Lock)
    next_id: int = 1
    starting: bool = False
    error: str | None = None

RUNNING: dict[str, ServerHandle] = {}   # server row id -> handle

def npx_path() -> str:
    p = shutil.which("npx.cmd") if os.name == "nt" else shutil.which("npx")
    if not p:
        raise ValueError("Node.js/npm (which provides `npx`) wasn't found. Install Node.js to use MCP servers.")
    return p

def list_installed() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM mcp_servers ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        h = RUNNING.get(d["id"])
        d["running"] = bool(h and h.proc and h.proc.returncode is None)
        d["tool_count"] = len(h.tools) if h else 0
        d["error"] = h.error if h else None
        out.append(d)
    return out

def install(key: str | None, name: str, command: str, args: list[str], path_arg: str | None, trusted: bool) -> str:
    sid = db.new_id()
    full_args = list(args) + ([path_arg] if path_arg else [])
    with db.get_conn() as conn:
        conn.execute("INSERT INTO mcp_servers (id, key, name, command, args_json, trusted, enabled, created_at) VALUES (?,?,?,?,?,?,1,?)",
                     (sid, key, name[:80], command, db.dumps(full_args), 1 if trusted else 0, db.now()))
    return sid

def remove(sid: str):
    asyncio.create_task(_stop(sid)) if RUNNING.get(sid) else None
    with db.get_conn() as conn:
        conn.execute("DELETE FROM mcp_servers WHERE id=?", (sid,))
    RUNNING.pop(sid, None)

async def _stop(sid: str):
    h = RUNNING.pop(sid, None)
    if h and h.proc and h.proc.returncode is None:
        h.proc.terminate()
        try:
            await asyncio.wait_for(h.proc.wait(), 5)
        except Exception:
            h.proc.kill()

async def _rpc(h: ServerHandle, method: str, params: dict, notify: bool = False, timeout: float = 20) -> dict | None:
    async with h.lock:
        mid = h.next_id; h.next_id += 1
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notify:
            msg["id"] = mid
        line = (json.dumps(msg) + "\n").encode()
        h.proc.stdin.write(line)
        await h.proc.stdin.drain()
        if notify:
            return None
        while True:
            raw = await asyncio.wait_for(h.proc.stdout.readline(), timeout)
            if not raw:
                raise RuntimeError("The MCP server closed its connection.")
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue          # server printed a non-JSON log line to stdout; skip it
            if obj.get("id") == mid:
                if "error" in obj:
                    raise RuntimeError(obj["error"].get("message", "MCP server error"))
                return obj.get("result", {})

async def start(sid: str) -> ServerHandle:
    existing = RUNNING.get(sid)
    if existing and existing.proc and existing.proc.returncode is None:
        return existing
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM mcp_servers WHERE id=?", (sid,)).fetchone()
    if not row:
        raise ValueError("Unknown server")
    h = ServerHandle(proc=None, starting=True)
    RUNNING[sid] = h
    try:
        args = db.loads(row["args_json"]) or []
        cmd = [npx_path(), "-y", row["command"], *args] if row["command"].startswith("@") else [row["command"], *args]
        proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                                     stderr=asyncio.subprocess.DEVNULL,
                                                     cwd=settings.data_dir)
        h.proc = proc
        await _rpc(h, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                     "clientInfo": {"name": "ai-brain-assistant", "version": "1"}}, timeout=15)
        await _rpc(h, "notifications/initialized", {}, notify=True)
        result = await _rpc(h, "tools/list", {}, timeout=15)
        h.tools = result.get("tools", [])
        h.starting = False
        return h
    except Exception as e:
        h.error = str(e)[:300]; h.starting = False
        if h.proc and h.proc.returncode is None:
            h.proc.terminate()
        raise ValueError(f"Couldn't start '{row['name']}': {h.error}")

async def stop(sid: str):
    await _stop(sid)

async def list_tools(sid: str) -> list[dict]:
    h = await start(sid)
    return h.tools

async def call_tool(sid: str, tool_name: str, arguments: dict, timeout: float = 60) -> dict:
    h = await start(sid)
    if not any(t["name"] == tool_name for t in h.tools):
        raise ValueError(f"'{tool_name}' is not a tool on this server.")
    result = await _rpc(h, "tools/call", {"name": tool_name, "arguments": arguments}, timeout=timeout)
    return result

async def stop_all():
    for sid in list(RUNNING):
        await _stop(sid)
