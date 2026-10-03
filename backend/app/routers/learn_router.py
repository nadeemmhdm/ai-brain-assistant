from fastapi import APIRouter, HTTPException
import asyncio
from pydantic import BaseModel
from .. import learn, errors

router = APIRouter(prefix="/api/learn", tags=["learn"])

class LearnRequest(BaseModel):
    topic: str

@router.post("")
async def start_learn(body: LearnRequest):
    topic = body.topic.strip()
    if not topic or len(topic) > 200:
        raise errors.http(400, "AIB-LRN-001", "Enter a topic (1-200 characters).")
    if learn.any_running():
        raise errors.http(409, "AIB-LRN-002", "Another Trusted Topic Learning session is already running.")
    try:
        session_id = learn.start_session(topic)
    except Exception as e:
        raise HTTPException(500, f"Couldn't start learning: {e}")
    return {"session_id": session_id}

@router.get("/active")
def active():
    """The currently running/paused session, if any -- lets the UI resume
    watching it instead of just failing to start a second one."""
    for sid, state in learn.SESSIONS.items():
        if state["status"] in ("running", "paused"):
            return {"session_id": sid, **state}
    return None

@router.get("/status")
def status(session_id: str):
    state = learn.SESSIONS.get(session_id)
    if not state:
        raise errors.http(404, "AIB-LRN-003", "Unknown learning session.")
    return state

@router.post("/pause")
def pause(session_id: str):
    state = learn.SESSIONS.get(session_id)
    if not state: raise errors.http(404, "AIB-LRN-003", "Unknown learning session.")
    if state["status"] in ("completed","cancelled","error"): return {"ok": False, "status": state["status"]}
    state["control"] = "pause"; state["status"] = "paused"; state["current_task"] = "Paused"
    return {"ok": True, "status": "paused"}

@router.post("/resume")
def resume(session_id: str):
    state = learn.SESSIONS.get(session_id)
    if not state: raise errors.http(404, "AIB-LRN-003", "Unknown learning session.")
    state["control"] = "run"; state["status"] = "running"; state["current_task"] = "Resuming trusted research…"
    return {"ok": True, "status": "running"}

@router.post("/cancel")
def cancel(session_id: str):
    state = learn.SESSIONS.get(session_id)
    if not state: raise errors.http(404, "AIB-LRN-003", "Unknown learning session.")
    state["control"] = "cancel"; state["current_task"] = "Cancelling…"
    task = learn.TASKS.get(session_id)
    if task and not task.done(): task.cancel()
    return {"ok": True, "status": "cancelling"}
