"""Stable, searchable error codes shared by API, Web UI and CLI."""
from __future__ import annotations
from fastapi import HTTPException

ERRORS = {
    "AIB-GEN-001": ("Unexpected internal error", "Retry once, then check the backend log."),
    "AIB-NET-001": ("Internet service is unreachable", "Check the network connection or continue in offline mode."),
    "AIB-AUTH-001": ("Authentication required", "Unlock AI Brain and retry."),
    "AIB-MDL-001": ("Local model server is unavailable", "Start/load the llama.cpp model server and retry."),
    "AIB-MDL-002": ("Invalid model request", "Check the model filename/path and role."),
    "AIB-MDL-003": ("Hugging Face is unreachable", "Check internet access and try again."),
    "AIB-MDL-004": ("Invalid Hugging Face token", "Verify the token and required permissions."),
    "AIB-LRN-001": ("Invalid learning topic", "Enter a topic between 1 and 200 characters."),
    "AIB-LRN-002": ("Learning session already running", "Wait, pause/cancel the active session, then retry."),
    "AIB-LRN-003": ("Unknown learning session", "Refresh the learning view and start a new session if needed."),
    "AIB-BRN-001": ("Invalid Brain knowledge input", "Provide a valid question and answer."),
    "AIB-TRN-001": ("Unknown training job", "Refresh Training and verify the job ID."),
    "AIB-UPD-001": ("Update cannot be installed safely", "Check local changes, Git availability and network access."),
}

def detail(code: str, message: str | None = None, hint: str | None = None) -> dict:
    title, default_hint = ERRORS.get(code, ("AI Brain error", "See docs/ERROR_CODES.md."))
    return {"code": code, "message": message or title, "hint": hint or default_hint}

def http(status: int, code: str, message: str | None = None, hint: str | None = None) -> HTTPException:
    return HTTPException(status, detail(code, message, hint))
