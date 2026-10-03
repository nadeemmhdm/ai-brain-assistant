from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx
import os
import re
from .. import llm_client, model_manager, downloads, vault, errors
from ..config import settings

router = APIRouter(prefix="/api/model", tags=["model"])

@router.get("/status")
async def status():
    main_status = await llm_client.check_model_status("main")
    agent_status = await llm_client.check_model_status("agent")
    assigned=model_manager.assignments()
    running=model_manager.running()
    return {
        "main": {**main_status, "name": assigned["main"] or running.get("main",{}).get("filename"), "assigned": assigned["main"]},
        "agent": {**agent_status, "name": assigned["agent"] or running.get("agent",{}).get("filename"), "assigned": assigned["agent"]},
        "reasoning_levels": list(settings.reasoning_levels.keys()),
        "default_reasoning_level": settings.default_reasoning_level,
        "models_dir": os.path.basename(os.path.normpath(settings.models_dir)) or "Models",
        "managed": model_manager.running(),
    }

@router.get("/local")
def local():
    return {"models_dir": os.path.basename(os.path.normpath(settings.models_dir)) or "Models", "models": model_manager.list_local(), "running": model_manager.running(), "assigned": model_manager.assignments()}


class AssignBody(BaseModel):
    role: str
    filename: str

@router.post("/assign")
def assign(body: AssignBody):
    try:
        return model_manager.set_assignment(body.role,body.filename)
    except ValueError as e:
        raise errors.http(400,"AIB-MDL-002",str(e))

@router.post("/assign/clear")
def clear_assignment(body: AssignBody):
    try:
        model_manager.clear_assignment(body.role)
        return {"ok":True}
    except ValueError as e:
        raise errors.http(400,"AIB-MDL-002",str(e))

class LoadBody(BaseModel):
    role: str
    filename: str

@router.post("/load")
def load(body: LoadBody):
    try:
        return model_manager.load(body.role, body.filename)
    except ValueError as e:
        raise errors.http(400, "AIB-MDL-002", str(e))

@router.post("/unload")
def unload(body: LoadBody):
    model_manager.unload(body.role)
    return {"ok": True}

@router.get("/hf/search")
def hf_search(q: str):
    try:
        return model_manager.hf_search(q)
    except httpx.HTTPError as e:
        raise errors.http(502, "AIB-MDL-003", f"Could not reach Hugging Face: {e}")

@router.get("/hf/files")
def hf_files(repo: str):
    try:
        return model_manager.hf_files(repo)
    except ValueError as e:
        raise errors.http(400, "AIB-MDL-002", str(e))
    except httpx.HTTPError as e:
        raise errors.http(502, "AIB-MDL-003", f"Could not reach Hugging Face: {e}")

class HFDownloadBody(BaseModel):
    repo: str
    filename: str

@router.post("/hf/download")
def hf_download(body: HFDownloadBody):
    try:
        return {"download_id": model_manager.hf_download(body.repo, body.filename)}
    except ValueError as e:
        raise errors.http(400, "AIB-MDL-002", str(e))

@router.get("/downloads")
def list_downloads(kind: str | None = None):
    return downloads.list_downloads(kind)

@router.post("/downloads/{did}/cancel")
def cancel(did: str):
    downloads.cancel(did)
    return {"ok": True}


# ---- browser file picker import ----------------------------------------------
# Browsers deliberately do not expose a real local filesystem path. Stream the
# selected GGUF to the app's local Models directory instead, without buffering
# multi-GB model files in RAM.
@router.post("/import/upload")
async def import_model_upload(request: Request):
    raw_name = request.headers.get("X-Model-Filename", "")
    name = os.path.basename(raw_name.strip().replace("\\", "/"))
    if not name.lower().endswith(".gguf") or not re.fullmatch(r"[A-Za-z0-9._() +\-]+\.gguf", name, re.I):
        raise errors.http(400, "AIB-MDL-002", "Select a valid .gguf model file.")
    os.makedirs(settings.models_dir, exist_ok=True)
    dest = os.path.join(settings.models_dir, name)
    part = dest + ".part"
    if os.path.exists(dest):
        raise errors.http(409, "AIB-MDL-002", f"{name} is already in the models folder.")
    written = 0
    try:
        with open(part, "wb") as out:
            async for chunk in request.stream():
                if chunk:
                    written += len(chunk)
                    out.write(chunk)
        if written < 4:
            raise ValueError("The selected file is empty or incomplete.")
        with open(part, "rb") as chk:
            if chk.read(4) != b"GGUF":
                raise ValueError("The selected file is not a valid GGUF model.")
        os.replace(part, dest)
        return {"filename": name, "mode": "upload", "size_mb": round(written / 1e6, 1)}
    except Exception as e:
        try:
            if os.path.exists(part): os.remove(part)
        except OSError:
            pass
        if isinstance(e, HTTPException):
            raise
        raise errors.http(400, "AIB-MDL-002", str(e))

# ---- import models you already have on disk ---------------------------------
class ImportModelBody(BaseModel):
    path: str
    mode: str = "link"        # link = use in place (no copy) | copy = copy into the models folder

@router.post("/import")
def import_model(body: ImportModelBody):
    try:
        return model_manager.import_model(body.path, body.mode)
    except (ValueError, OSError) as e:
        raise errors.http(400, "AIB-MDL-002", str(e))

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
        raise errors.http(400, "AIB-MDL-004", "That doesn't look like a Hugging Face token.")
    try:
        r = httpx.get("https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {tok}"}, timeout=10)
    except httpx.HTTPError:
        raise errors.http(502, "AIB-MDL-003", "Couldn't reach Hugging Face to check the token.")
    if r.status_code != 200:
        raise errors.http(400, "AIB-MDL-004", "Hugging Face rejected that token.")
    try:
        vault.put("hf_token", tok)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return {"set": True, "user": r.json().get("name")}

@router.delete("/hf/token")
def hf_token_clear():
    vault.delete("hf_token")
    return {"set": False}
