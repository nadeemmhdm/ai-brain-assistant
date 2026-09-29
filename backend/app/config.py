"""
Central configuration. Everything here can be overridden with environment
variables (see .env.example). Nothing here is exposed to the frontend --
the React app only ever talks to THIS backend, never directly to a model
server or to any API key.
"""
import os
from dataclasses import dataclass, field

def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)

@dataclass
class Settings:
    # -- llama.cpp servers ---------------------------------------------
    # Run each GGUF model with `llama-server`, e.g.:
    #   llama-server -m C:\Users\nadee\PersonalAi\Models\qwen2.5-1.5b-instruct-q4_k_m.gguf --port 8081
    #   llama-server -m C:\Users\nadee\PersonalAi\Models\qwen2.5-0.5b-instruct-q4_k_m.gguf --port 8082
    main_model_url: str = field(default_factory=lambda: _env("MAIN_MODEL_URL", "http://127.0.0.1:8081"))
    agent_model_url: str = field(default_factory=lambda: _env("AGENT_MODEL_URL", "http://127.0.0.1:8082"))
    main_model_name: str = field(default_factory=lambda: _env("MAIN_MODEL_NAME", "qwen2.5-1.5b-instruct"))
    agent_model_name: str = field(default_factory=lambda: _env("AGENT_MODEL_NAME", "qwen2.5-0.5b-instruct"))

    # -- server -----------------------------------------------------------
    host: str = field(default_factory=lambda: _env("BACKEND_HOST", "127.0.0.1"))  # localhost-only by default
    port: int = field(default_factory=lambda: int(_env("BACKEND_PORT", "8000")))
    allowed_origins: list = field(default_factory=lambda: _env("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(","))

    # -- storage ------------------------------------------------------------
    data_dir: str = field(default_factory=lambda: _env("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data")))

    # -- reasoning levels ---------------------------------------------------
    # "off" skips the thinking step entirely (fastest, no <thinking> block).
    reasoning_levels: dict = field(default_factory=lambda: {
        "off":    {"temperature": 0.6, "max_tokens": 512,  "think": False, "think_budget": 0},
        "low":    {"temperature": 0.5, "max_tokens": 768,  "think": True,  "think_budget": 120},
        "medium": {"temperature": 0.5, "max_tokens": 1024, "think": True,  "think_budget": 300},
        "high":   {"temperature": 0.4, "max_tokens": 1536, "think": True,  "think_budget": 600},
        "max":    {"temperature": 0.3, "max_tokens": 2048, "think": True,  "think_budget": 1200},
    })
    default_reasoning_level: str = "medium"

    # -- model manager (load GGUFs from a folder, download from Hugging Face) --
    models_dir: str = field(default_factory=lambda: _env("MODELS_DIR", r"C:\Users\nadee\PersonalAi\Models" if os.name == "nt" else os.path.expanduser("~/PersonalAi/Models")))
    llama_server_path: str = field(default_factory=lambda: _env("LLAMA_SERVER_PATH", "llama-server"))
    llama_threads: int = field(default_factory=lambda: int(_env("LLAMA_THREADS", str(max(1, (os.cpu_count() or 4) - 1)))))
    llama_ctx: int = field(default_factory=lambda: int(_env("LLAMA_CTX", "8192")))
    llama_gpu_layers: int = field(default_factory=lambda: int(_env("LLAMA_GPU_LAYERS", "0")))
    hf_token: str = field(default_factory=lambda: _env("HF_TOKEN", ""))  # optional, backend-only

    # -- voice (all optional; see requirements-voice.txt) -------------------
    voice_dir: str = field(default_factory=lambda: _env("VOICE_DIR", os.path.join(os.path.dirname(__file__), "..", "data", "voice")))

    # -- google (your own OAuth client; never sent to the browser) ---------
    google_client_id: str = field(default_factory=lambda: _env("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: _env("GOOGLE_CLIENT_SECRET", ""))
    google_redirect_uri: str = field(default_factory=lambda: _env("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/google/callback"))

    # -- research / trust ------------------------------------------------
    request_delay_seconds: float = 1.0
    max_sources_per_question: int = 5
    user_agent: str = "AI-Brain-ResearchAgent/0.1 (local, respects robots.txt)"

settings = Settings()
os.makedirs(settings.data_dir, exist_ok=True)
os.makedirs(settings.voice_dir, exist_ok=True)
