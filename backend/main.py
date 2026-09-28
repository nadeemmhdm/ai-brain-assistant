r"""
Entry point.

    cd backend
    python -m venv .venv && source .venv/bin/activate   (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt
    uvicorn main:app --host 127.0.0.1 --port 8000

Or from the repo root: `python scripts/run_dev.py` starts this AND the
frontend dev server together.

Binds to 127.0.0.1 by default -- no public exposure (section 28).
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app import auth
from app.routers import (
    chat, learn_router, brain_router, settings_router, models_router,
    mcp_router, auth_router, dataset_router, training_router,
)

app = FastAPI(title="AI Brain - Local Assistant", version="0.2.0-beta.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    init_db()

# Unprotected: health check and the auth flow itself.
app.include_router(auth_router.router)

# Protected: once a passphrase is set (see app/auth.py -- off by default),
# these all require a valid session token. Until then, auth.require_auth
# is a no-op and everything works exactly as before.
_protected = [Depends(auth.require_auth)]
app.include_router(chat.router, dependencies=_protected)
app.include_router(learn_router.router, dependencies=_protected)
app.include_router(brain_router.router, dependencies=_protected)
app.include_router(settings_router.router, dependencies=_protected)
app.include_router(models_router.router, dependencies=_protected)
app.include_router(mcp_router.router, dependencies=_protected)
app.include_router(dataset_router.router, dependencies=_protected)
app.include_router(training_router.router, dependencies=_protected)

@app.get("/api/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
