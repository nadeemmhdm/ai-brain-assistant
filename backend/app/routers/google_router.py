from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from html import escape
from pydantic import BaseModel
from .. import google_api as g, actions

router = APIRouter(prefix="/api/google", tags=["google"])
public = APIRouter(prefix="/api/google", tags=["google"])   # OAuth redirect target (browser navigation, no bearer header)

def _err(e: g.GoogleError):
    raise HTTPException(e.status, str(e))

@router.get("/status")
def status():
    return g.status()

@router.get("/connect")
def connect():
    try:
        return {"url": g.auth_url()}
    except g.GoogleError as e:
        _err(e)

@public.get("/callback")
def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        return HTMLResponse(f"<h3>Google sign-in was cancelled.</h3><p>{escape(error or '')}</p>You can close this tab.", status_code=400)
    try:
        g.handle_callback(code, state)
    except g.GoogleError as e:
        return HTMLResponse(f"<h3>Couldn't connect Google</h3><p>{escape(str(e))}</p>", status_code=400)
    return HTMLResponse("<script>window.opener&&window.opener.postMessage('google-connected',window.location.origin);window.close()</script>"
                        "<h3>✅ Google connected.</h3>You can close this tab and return to the app.")

@router.post("/disconnect")
def disconnect():
    g.disconnect()
    return {"ok": True}

@router.get("/actions")
def list_actions():
    return [actions.describe(a) for a in actions.ACTIONS]

class ExecuteBody(BaseModel):
    action: str
    params: dict = {}
    grant: str = "once"            # once | chat | always -- the person's choice in the permission dialog
    conversation_id: str | None = None

@router.post("/execute")
def execute(body: ExecuteBody):
    if body.action not in actions.ACTIONS:
        raise HTTPException(400, "Unknown action")
    if body.grant not in ("once", "chat", "always", "standing"):
        raise HTTPException(400, "Invalid grant")
    if body.grant == "standing":       # use an existing saved permission; nothing new is granted
        if not actions.has_grant(body.action, body.conversation_id):
            raise HTTPException(403, "Permission needed")
    else:
        actions.add_grant(body.action, body.grant, body.conversation_id)
    try:
        return {"result": actions.run(body.action, body.params)}
    except g.GoogleError as e:
        _err(e)
    except KeyError as e:
        raise HTTPException(400, f"Missing field: {e}")

@router.get("/permissions")
def permissions():
    return actions.list_grants()

@router.delete("/permissions/{grant_id}")
def revoke(grant_id: str):
    actions.revoke(grant_id)
    return {"ok": True}

@router.get("/has-permission")
def has_permission(action: str, conversation_id: str | None = None):
    return {"granted": actions.has_grant(action, conversation_id)}
