"""
Local voice: speech-to-text (faster-whisper) and text-to-speech (Piper).

Both are OPTIONAL (see requirements-voice.txt). Models/voices are
downloaded once, on request, while you're online -- after that they load
from disk with no network. If they aren't installed, the web UI falls back
to the browser's built-in voice features (which work without any setup,
though the browser's speech *recognition* may use the internet).
"""
import io
import json
import os
import re
import tempfile
import threading
import wave
import httpx
from .config import settings
from . import downloads

STT_DIR = os.path.join(settings.voice_dir, "whisper")
TTS_DIR = os.path.join(settings.voice_dir, "piper")
os.makedirs(STT_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

STT_SIZES = {"tiny.en": 75, "base.en": 145, "small.en": 480, "tiny": 75, "base": 145, "small": 480}  # approx MB
VOICE_ID_RE = re.compile(r"^([a-z]{2})_([A-Z]{2})-([\w]+)-([a-z_]+)$")

CURATED_VOICES = ["en_US-lessac-medium", "en_US-amy-medium", "en_US-ryan-medium", "en_GB-alan-medium",
                  "en_GB-jenny_dioco-medium", "hi_IN-pratham-medium", "hi_IN-priyamvada-medium"]

_stt_model = {}
_stt_install: dict[str, dict] = {}
_tts_voices = {}

def stt_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False

def tts_available() -> bool:
    try:
        import piper  # noqa: F401
        return True
    except ImportError:
        return False

def installed_stt() -> list[str]:
    out = []
    for size in STT_SIZES:
        if os.path.isdir(os.path.join(STT_DIR, f"models--Systran--faster-whisper-{size}")):
            out.append(size)
    return out

def installed_voices() -> list[str]:
    return sorted(f[:-5] for f in os.listdir(TTS_DIR) if f.endswith(".onnx") and os.path.exists(os.path.join(TTS_DIR, f + ".json")))

def status() -> dict:
    return {
        "stt": {"library": stt_available(), "installed": installed_stt(), "installing": _stt_install,
                "sizes_mb": STT_SIZES},
        "tts": {"library": tts_available(), "voices": installed_voices()},
    }

# ---- STT --------------------------------------------------------------------
def install_stt(size: str) -> None:
    if size not in STT_SIZES:
        raise ValueError("Unknown model size")
    if not stt_available():
        raise ValueError("faster-whisper is not installed. Run: pip install -r backend/requirements-voice.txt")
    if _stt_install.get(size, {}).get("status") == "running":
        return
    _stt_install[size] = {"status": "running", "error": None}
    def work():
        try:
            from faster_whisper import WhisperModel
            WhisperModel(size, device="cpu", compute_type="int8", download_root=STT_DIR)  # downloads once
            _stt_install[size] = {"status": "completed", "error": None}
        except Exception as e:
            _stt_install[size] = {"status": "failed", "error": str(e)[:300]}
    threading.Thread(target=work, daemon=True).start()

def _get_stt(size: str):
    if size not in _stt_model:
        from faster_whisper import WhisperModel
        _stt_model[size] = WhisperModel(size, device="cpu", compute_type="int8", download_root=STT_DIR, local_files_only=True)
    return _stt_model[size]

def transcribe(audio: bytes, size: str | None = None, language: str | None = None) -> str:
    have = installed_stt()
    if not have:
        raise ValueError("No speech model installed yet. Install one in Settings → Voice (needs internet once).")
    size = size if size in have else have[0]
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio); path = f.name
    try:
        segments, _ = _get_stt(size).transcribe(path, language=language or None, beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        try: os.remove(path)
        except OSError: pass

# ---- TTS --------------------------------------------------------------------
def voice_urls(voice_id: str) -> list[tuple[str, str]]:
    m = VOICE_ID_RE.match(voice_id)
    if not m:
        raise ValueError("Voice ids look like en_US-lessac-medium")
    lang, region, name, quality = m.groups()
    sub = f"{lang}/{lang}_{region}/{name}/{quality}"
    return [(downloads.hf_url("rhasspy/piper-voices", f"{voice_id}.onnx", sub), os.path.join(TTS_DIR, f"{voice_id}.onnx")),
            (downloads.hf_url("rhasspy/piper-voices", f"{voice_id}.onnx.json", sub), os.path.join(TTS_DIR, f"{voice_id}.onnx.json"))]

def install_voice(voice_id: str) -> list[str]:
    pairs = voice_urls(voice_id)
    return [downloads.start("voice", url, dest) for url, dest in pairs if not os.path.exists(dest)]

def catalog() -> list[dict]:
    """All Piper voices (needs internet the first time), else a curated list."""
    cache = os.path.join(settings.voice_dir, "voices.json")
    data = None
    try:
        r = httpx.get("https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json", follow_redirects=True, timeout=15)
        r.raise_for_status(); data = r.json()
        with open(cache, "w", encoding="utf-8") as f: json.dump(data, f)
    except Exception:
        if os.path.exists(cache):
            data = json.load(open(cache, encoding="utf-8"))
    if data:
        out = [{"id": k, "language": v.get("language", {}).get("name_english", ""), "quality": v.get("quality", "")} for k, v in data.items()]
        return sorted(out, key=lambda x: x["id"])
    return [{"id": v, "language": v.split("-")[0], "quality": v.split("-")[-1]} for v in CURATED_VOICES]

def _load_voice(voice_id: str):
    if voice_id not in _tts_voices:
        from piper import PiperVoice
        p = os.path.join(TTS_DIR, f"{voice_id}.onnx")
        _tts_voices[voice_id] = PiperVoice.load(p, config_path=p + ".json")
    return _tts_voices[voice_id]

def synthesize(text: str, voice_id: str | None = None) -> bytes:
    have = installed_voices()
    if not have:
        raise ValueError("No voice installed yet. Download one in Settings → Voice (needs internet once).")
    voice_id = voice_id if voice_id in have else have[0]
    voice = _load_voice(voice_id)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        if hasattr(voice, "synthesize_wav"):      # piper-tts >= 1.3
            voice.synthesize_wav(text[:1200], wf)
        else:                                     # piper-tts 1.2
            voice.synthesize(text[:1200], wf)
    return buf.getvalue()
