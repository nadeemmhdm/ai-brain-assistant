from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import memory

router = APIRouter(prefix="/api/memory", tags=["memory"])

class MemoryBody(BaseModel):
    content: str

@router.get("")
def list_memories():
    return memory.list_all()

@router.post("")
def add_memory(body: MemoryBody):
    text = body.content.strip()
    if not 3 <= len(text) <= 300:
        raise HTTPException(400, "Memory must be 3-300 characters.")
    return {"id": memory.add(text)}

@router.delete("/{mid}")
def delete_memory(mid: str):
    memory.delete(mid)
    return {"ok": True}
