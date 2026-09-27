from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import learn

router = APIRouter(prefix="/api/learn", tags=["learn"])

class LearnRequest(BaseModel):
    topic: str

@router.post("")
def start_learn(body: LearnRequest):
    session_id = learn.start_session(body.topic)
    return {"session_id": session_id}

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
