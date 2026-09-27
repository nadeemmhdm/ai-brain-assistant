r"""
Entry point.

    cd backend
    python -m venv .venv && source .venv/bin/activate   (Windows: .venv\Scripts\activate)
    pip install -r requirements.txt
    uvicorn main:app --host 127.0.0.1 --port 8000

Binds to 127.0.0.1 by default -- no public exposure (section 28).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.routers import chat, learn_router, brain_router, settings_router, models_router, mcp_router

app = FastAPI(title="AI Brain - Local Assistant", version="0.1.0")

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

app.include_router(chat.router)
app.include_router(learn_router.router)
app.include_router(brain_router.router)
app.include_router(settings_router.router)
app.include_router(models_router.router)
app.include_router(mcp_router.router)

@app.get("/api/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
