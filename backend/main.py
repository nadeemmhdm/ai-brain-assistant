r"""
Entry point.

    cd backend
    python -m venv .venv && source .venv/bin/activate   (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt
    uvicorn main:app --host 127.0.0.1 --port 8000

Or from the repo root: `python scripts/run_dev.py` starts this AND the
frontend dev server together. Binds to 127.0.0.1 by default.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.routers import settings_router
from app import auth, brain, teach, llm_client, model_manager, version, updater, skills, mcp_client
from app.routers import (
    chat, learn_router, brain_router, settings_router, models_router, mcp_router,
    auth_router, dataset_router, training_router, memory_router, voice_router,
    google_router, updates_router, skills_router, translate_router,
)

async def _is_online() -> bool:
    try:
        _, w = await asyncio.wait_for(asyncio.open_connection("1.1.1.1", 443), 3)
        w.close()
        return True
    except Exception:
        return False

async def _models_ready() -> bool:
    return (await llm_client.check_model_status("main"))["online"] or (await llm_client.check_model_status("agent"))["online"]

def _maybe_auto_update():
    """Opt-in only (Settings -> Updates). Installs official release tags via fast-forward."""
    try:
        if settings_router.get_value("auto_install_updates") == "true" and updater.is_git_checkout():
            if updater.check(force=True)["update_available"]:
                updater.install()
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await asyncio.to_thread(brain.reembed_if_needed)
    await asyncio.to_thread(skills.seed)
    task = asyncio.create_task(teach.scheduler_loop(_is_online, _models_ready))
    await asyncio.to_thread(_maybe_auto_update)
    yield
    task.cancel()
    model_manager.shutdown_all()
    await mcp_client.stop_all()

app = FastAPI(title="AI Brain - Local Assistant", version=version.current(), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unprotected: health, the auth flow itself, and Google's OAuth redirect target.
app.include_router(auth_router.router)
app.include_router(google_router.public)

# Protected: once a passphrase is set (off by default) these need a session token.
_protected = [Depends(auth.require_auth)]
for r in (chat.router, learn_router.router, brain_router.router, settings_router.router, models_router.router,
          mcp_router.router, dataset_router.router, training_router.router, memory_router.router,
          voice_router.router, google_router.router, updates_router.router, skills_router.router,
          translate_router.router):
    app.include_router(r, dependencies=_protected)

@app.get("/api/health")
def health():
    return {"ok": True, "version": version.current()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
