from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from .. import llm_client, model_manager, downloads, vault
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
        "models_dir": settings.models_dir,
        "managed": model_manager.running(),
    }

@router.get("/local")
def local():
    return {"models_dir": settings.models_dir, "models": model_manager.list_local(), "running": model_manager.running()}

class LoadBody(BaseModel):
    role: str
    filename: str

@router.post("/load")
def load(body: LoadBody):
    try:
        return model_manager.load(body.role, body.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/unload")
def unload(body: LoadBody):
    model_manager.unload(body.role)
    return {"ok": True}

@router.get("/hf/search")
def hf_search(q: str):
    try:
        return model_manager.hf_search(q)
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Could not reach Hugging Face (are you online?): {e}")

@router.get("/hf/files")
def hf_files(repo: str):
    try:
        return model_manager.hf_files(repo)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Could not reach Hugging Face (are you online?): {e}")

class HFDownloadBody(BaseModel):
    repo: str
    filename: str

@router.post("/hf/download")
def hf_download(body: HFDownloadBody):
    try:
        return {"download_id": model_manager.hf_download(body.repo, body.filename)}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/downloads")
def list_downloads(kind: str | None = None):
    return downloads.list_downloads(kind)

@router.post("/downloads/{did}/cancel")
def cancel(did: str):
    downloads.cancel(did)
    return {"ok": True}


# ---- import models you already have on disk ---------------------------------
class ImportModelBody(BaseModel):
    path: str
    mode: str = "link"        # link = use in place (no copy) | copy = copy into the models folder

@router.post("/import")
def import_model(body: ImportModelBody):
    try:
        return model_manager.import_model(body.path, body.mode)
    except (ValueError, OSError) as e:
        raise HTTPException(400, str(e))

class RemoveImportBody(BaseModel):
    filename: str

@router.post("/import/remove")
def remove_import(body: RemoveImportBody):
    model_manager.remove_import(body.filename)
    return {"ok": True}

# ---- Hugging Face access token (write-only: stored encrypted, never returned) -
class HFTokenBody(BaseModel):
    token: str

@router.get("/hf/token")
def hf_token_status():
    return {"set": bool(downloads.hf_token())}

@router.post("/hf/token")
def hf_token_set(body: HFTokenBody):
    tok = body.token.strip()
    if not tok.startswith("hf_") or len(tok) < 20 or len(tok) > 200:
        raise HTTPException(400, "That doesn't look like a Hugging Face token (they start with hf_).")
    try:
        r = httpx.get("https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(502, "Couldn't reach Hugging Face to check the token — are you online?")
    if r.status_code != 200:
        raise HTTPException(400, "Hugging Face rejected that token.")
    try:
        vault.put("hf_token", tok)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"set": True, "user": r.json().get("name")}

@router.delete("/hf/token")
def hf_token_clear():
    vault.delete("hf_token")
    return {"set": False}
