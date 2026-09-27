"""
Thin client for talking to local llama.cpp `llama-server` instances
(OpenAI-compatible /v1/chat/completions). No API key is ever used here --
these are local processes on 127.0.0.1.

Reasoning levels do NOT change model weights (these are small instruct
models, not literal "thinking" models). Instead a level controls:
  - whether the model is asked to reason in a <thinking>...</thinking>
    block before its final answer (parsed out and shown as a collapsible
    "thought process" in the UI's thinking animation)
  - how much of the token budget is allowed for that scratchpad
  - sampling temperature / max_tokens

"off" skips the scratchpad step entirely for the fastest response.
"""
import json
import httpx
from typing import AsyncGenerator, Optional
from .config import settings

THINK_SYSTEM_SUFFIX = (
    "\n\nBefore answering, think step by step inside a single "
    "<thinking>...</thinking> block (keep it under {budget} words), "
    "then give your final answer after the block. Never mention these "
    "instructions to the user."
)

def _model_url(which: str) -> str:
    return settings.main_model_url if which == "main" else settings.agent_model_url

def _model_name(which: str) -> str:
    return settings.main_model_name if which == "main" else settings.agent_model_name

def build_system_prompt(base_prompt: str, reasoning_level: str) -> str:
    cfg = settings.reasoning_levels.get(reasoning_level, settings.reasoning_levels[settings.default_reasoning_level])
    if cfg["think"]:
        return base_prompt + THINK_SYSTEM_SUFFIX.format(budget=cfg["think_budget"])
    return base_prompt

def split_thinking(raw_text: str) -> tuple[Optional[str], str]:
    """Pull a <thinking>...</thinking> block out of a full completion."""
    start, end = "<thinking>", "</thinking>"
    if start in raw_text and end in raw_text:
        pre, rest = raw_text.split(start, 1)
        thought, answer = rest.split(end, 1)
        return thought.strip(), (pre + answer).strip()
    return None, raw_text.strip()

async def check_model_status(which: str) -> dict:
    url = _model_url(which)
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{url}/health")
            ok = r.status_code == 200
    except Exception as e:
        return {"model": which, "url": url, "online": False, "error": str(e)}
    return {"model": which, "url": url, "online": ok}

async def stream_chat(
    which: str,
    messages: list[dict],
    reasoning_level: str,
) -> AsyncGenerator[str, None]:
    """Yields raw text deltas from the local model server (SSE passthrough)."""
    cfg = settings.reasoning_levels.get(reasoning_level, settings.reasoning_levels[settings.default_reasoning_level])
    url = _model_url(which)
    payload = {
        "model": _model_name(which),
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "stream": True,
    }
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{url}/v1/chat/completions", json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    yield f"__ERROR__:Model server ({which}) returned {resp.status_code}: {body.decode(errors='ignore')[:300]}"
                    return
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue
    except httpx.ConnectError:
        yield (
            f"__ERROR__:Could not reach the local {which} model server at {url}. "
            f"Start it first, e.g.\n"
            f"llama-server -m \"C:\\Users\\nadee\\PersonalAi\\Models\\"
            f"{'qwen2.5-1.5b-instruct-q4_k_m.gguf' if which == 'main' else 'qwen2.5-0.5b-instruct-q4_k_m.gguf'}\" "
            f"--port {url.rsplit(':', 1)[-1]}"
        )

async def complete(which: str, messages: list[dict], reasoning_level: str) -> str:
    """Non-streaming helper, used by the research agent for small tasks."""
    chunks = []
    async for delta in stream_chat(which, messages, reasoning_level):
        if delta.startswith("__ERROR__:"):
            return ""
        chunks.append(delta)
    return "".join(chunks)
