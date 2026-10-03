from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from .. import teacher_mode,cloud_training

router=APIRouter(prefix="/api/teacher",tags=["teacher"])
class Lesson(BaseModel):
    topic:str
    question:str

@router.get("/status")
def status():
    return cloud_training.status()

@router.post("/lesson")
async def lesson(body:Lesson):
    if not body.topic.strip() or not body.question.strip(): raise HTTPException(400,"Topic and question are required")
    try: return await teacher_mode.lesson(body.topic.strip()[:200],body.question.strip()[:4000])
    except RuntimeError as e: raise HTTPException(409,str(e))
    except Exception as e: raise HTTPException(502,f"Teacher session failed: {type(e).__name__}: {e}")
