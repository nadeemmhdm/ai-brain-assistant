from fastapi import APIRouter
from .. import llm_client
from ..config import settings

router = APIRouter(prefix="/api/model", tags=["model"])

@router.get("/status")
async def status():
    main_status = await llm_client.check_model_status("main")
    agent_status = await llm_client.check_model_status("agent")
    return {
        "main": {**main_status, "name": settings.main_model_name},
        "agent": {**agent_status, "name": settings.agent_model_name},
        "reasoning_levels": list(settings.reasoning_levels.keys()),
        "default_reasoning_level": settings.default_reasoning_level,
    }
