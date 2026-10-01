from fastapi import APIRouter, HTTPException
import asyncio
from pydantic import BaseModel
from .. import learn

router = APIRouter(prefix="/api/learn", tags=["learn"])

class LearnRequest(BaseModel):
    topic: str

@router.post("")
async def start_learn(body: LearnRequest):
    topic = body.topic.strip()
    if not topic or len(topic) > 200:
        raise HTTPException(400, "Enter a topic (1-200 characters).")
    if learn.any_running():
        raise HTTPException(409, "Another Auto Learn session is already running. Wait for it to finish, or cancel it first.")
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
        raise HTTPException(404, "Unknown session_id")
    return state

@router.post("/pause")
def pause(session_id: str):
    if session_id in learn.SESSIONS:
        learn.SESSIONS[session_id]["control"] = "pause"
    return {"ok": True}

@router.post("/resume")
def resume(session_id: str):
    if session_id in learn.SESSIONS:
        learn.SESSIONS[session_id]["control"] = "run"
    return {"ok": True}

@router.post("/cancel")
def cancel(session_id: str):
    if session_id in learn.SESSIONS:
        learn.SESSIONS[session_id]["control"] = "cancel"
    return {"ok": True}
