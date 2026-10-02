import asyncio
import os
import subprocess
import sys
import threading
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from .. import voice
from .settings_router import get_value

router = APIRouter(prefix="/api/voice", tags=["voice"])
_SETUP = {"status": "idle", "error": None}

@router.get("/status")
def status():
    return voice.status()

@router.get("/setup/status")
def setup_status():
    return _SETUP

@router.post("/setup")
def setup_local_voice():
    if _SETUP["status"] == "running":
        return _SETUP
    req = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "requirements-voice.txt"))
    _SETUP.update(status="running", error=None)
    def work():
        try:
            p = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req], capture_output=True, text=True, timeout=1800)
            if p.returncode:
                raise RuntimeError((p.stderr or p.stdout)[-1200:])
            _SETUP.update(status="completed", error=None)
        except Exception as e:
            _SETUP.update(status="failed", error=str(e)[:1200])
    threading.Thread(target=work, daemon=True).start()
    return _SETUP

@router.get("/catalog")
async def catalog():
    return await asyncio.to_thread(voice.catalog)

class SttInstall(BaseModel):
    size: str = "base.en"

@router.post("/stt/install")
def stt_install(body: SttInstall):
    try:
        voice.install_stt(body.size)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}

class VoiceInstall(BaseModel):
    voice_id: str

@router.post("/tts/install")
def tts_install(body: VoiceInstall):
    try:
        return {"download_ids": voice.install_voice(body.voice_id)}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/stt")
async def stt(request: Request):
    audio = await request.body()
    if not audio or len(audio) > 15 * 1024 * 1024:
        raise HTTPException(400, "Send 1 byte – 15 MB of audio")
    try:
        text = await asyncio.to_thread(voice.transcribe, audio)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {e}")
    return {"text": text}

class TtsBody(BaseModel):
    text: str
    voice: str | None = None

@router.post("/tts")
async def tts(body: TtsBody):
    if not body.text.strip():
        raise HTTPException(400, "Empty text")
    try:
        wav = await asyncio.to_thread(voice.synthesize, body.text, body.voice or get_value("tts_voice") or None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Speech synthesis failed: {e}")
    return Response(wav, media_type="audio/wav")
