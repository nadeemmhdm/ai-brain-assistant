from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import skills

router = APIRouter(prefix="/api/skills", tags=["skills"])

@router.get("")
def list_all():
    return skills.list_all()

class SkillBody(BaseModel):
    name: str
    description: str = ""
    instructions: str
    icon: str = "Sparkles"

@router.post("")
def create(body: SkillBody):
    if len(body.name.strip()) < 2 or len(body.instructions.strip()) < 5:
        raise HTTPException(400, "Give the skill a name and some instructions.")
    return {"id": skills.create(body.name, body.description, body.instructions, body.icon)}

@router.put("/{sid}")
def update(sid: str, body: SkillBody):
    if not skills.get(sid):
        raise HTTPException(404, "Skill not found")
    skills.update(sid, body.name, body.description, body.instructions, body.icon)
    return {"ok": True}

@router.delete("/{sid}")
def delete(sid: str):
    s = skills.get(sid)
    if s and s["builtin"]:
        raise HTTPException(400, "Built-in skills can't be deleted, only edited.")
    skills.delete(sid)
    return {"ok": True}
