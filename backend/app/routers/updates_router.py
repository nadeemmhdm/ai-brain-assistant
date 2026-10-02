from fastapi import APIRouter, HTTPException
import asyncio
from .. import updater, errors
from .settings_router import get_value

router = APIRouter(prefix="/api/updates", tags=["updates"])

@router.get("")
async def check(force: bool = False):
    return await asyncio.to_thread(updater.check, force)

@router.post("/install")
async def install():
    try:
        return await asyncio.to_thread(updater.install)
    except ValueError as e:
        raise errors.http(400, "AIB-UPD-001", str(e))
