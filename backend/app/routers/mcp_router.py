"""
MCP (Model Context Protocol) connectors -- section requested by the user
but not part of the original written spec. This is an honest stub: it
lists connector status but does not fabricate live connections. Marked
Experimental everywhere in the UI until a real MCP client is wired in.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

# Not yet implemented: this app has no MCP client wired up. We return an
# honest empty/experimental list rather than pretending connectors work.
@router.get("/connectors")
def list_connectors():
    return {
        "status": "experimental",
        "note": "MCP connectors are not wired up in this build. This endpoint is a placeholder "
                "so the UI has something real to reflect. Implementing a local MCP client "
                "(stdio or SSE transport) is the next step.",
        "connectors": [],
    }
