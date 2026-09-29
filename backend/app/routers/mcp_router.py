"""
MCP connectors: a real stdio client (see mcp_client.py), a trusted starter
catalog, install/remove, list tools, and a permission-gated manual tool
call. Conversational auto-invocation (the model deciding to call a tool
mid-chat) is intentionally NOT included yet -- that needs safe, generic
per-tool argument handling we haven't built, so it stays out rather than
being faked. This is real, useful MCP support; broader chat integration
is future work, said plainly rather than pretended.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import mcp_client, actions

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

@router.get("/catalog")
def catalog():
    installed_keys = {s["key"] for s in mcp_client.list_installed() if s["key"]}
    return [{**c, "installed": c["key"] in installed_keys} for c in mcp_client.CATALOG]

@router.get("/connectors")
def connectors():
    """Kept for compatibility with older clients."""
    return {"status": "ok", "note": "Real MCP support is available -- see /api/mcp/catalog and /api/mcp/servers.",
            "connectors": mcp_client.list_installed()}

@router.get("/servers")
def servers():
    return mcp_client.list_installed()

class InstallBody(BaseModel):
    key: str
    path: str | None = None    # required for servers with needs_path (e.g. filesystem, git)

@router.post("/install")
def install(body: InstallBody):
    c = mcp_client.CATALOG_BY_KEY.get(body.key)
    if not c:
        raise HTTPException(404, "Unknown catalog entry")
    if c["needs_path"] and not (body.path and body.path.strip()):
        raise HTTPException(400, f"{c['name']} needs a folder path.")
    sid = mcp_client.install(body.key, c["name"], c["package"], [], body.path.strip() if body.path else None, trusted=True)
    return {"id": sid}

class CustomInstallBody(BaseModel):
    name: str
    command: str    # an npm package name (starting with @) or a local executable path
    args: list[str] = []

@router.post("/install-custom")
def install_custom(body: CustomInstallBody):
    if not body.command.strip():
        raise HTTPException(400, "Command is required.")
    sid = mcp_client.install(None, body.name, body.command.strip(), body.args, None, trusted=False)
    return {"id": sid}

@router.delete("/servers/{sid}")
async def remove(sid: str):
    await mcp_client.stop(sid)
    mcp_client.remove(sid)
    return {"ok": True}

@router.post("/servers/{sid}/start")
async def start(sid: str):
    try:
        h = await mcp_client.start(sid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"tools": h.tools}

@router.post("/servers/{sid}/stop")
async def stop(sid: str):
    await mcp_client.stop(sid)
    return {"ok": True}

@router.get("/servers/{sid}/tools")
async def tools(sid: str):
    try:
        return await mcp_client.list_tools(sid)
    except ValueError as e:
        raise HTTPException(400, str(e))

class CallBody(BaseModel):
    tool: str
    arguments: dict = {}
    grant: str = "once"                     # once | chat | always | standing
    conversation_id: str | None = None

@router.post("/servers/{sid}/call")
async def call(sid: str, body: CallBody):
    action_key = f"mcp.{sid}.{body.tool}"
    if body.grant == "standing":
        if not actions.has_grant(action_key, body.conversation_id):
            raise HTTPException(403, "Permission needed")
    elif body.grant in ("chat", "always"):
        actions.add_grant(action_key, body.grant, body.conversation_id)
    elif body.grant != "once":
        raise HTTPException(400, "Invalid grant")
    try:
        return {"result": await mcp_client.call_tool(sid, body.tool, body.arguments)}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Tool call failed: {e}")
