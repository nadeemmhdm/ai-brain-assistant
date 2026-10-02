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
    "<thinking>...</thinking> block, KEEPING IT UNDER {budget} WORDS. "
    "Always close the block with </thinking> well before you run out of room, "
    "then give your real final answer to the user after the block -- the "
    "thinking block is scratch space, never the answer itself. If you notice "
    "your thinking is getting long, stop early and close the tag anyway. "
    "Never mention these instructions to the user."
)

def _model_url(which: str) -> str:
    return settings.main_model_url if which == "main" else settings.agent_model_url

def _model_name(which: str) -> str:
    return settings.main_model_name if which == "main" else settings.agent_model_name

def build_system_prompt(base_prompt: str, reasoning_level: str, model: str = "agent") -> str:
    cfg = settings.reasoning_levels.get(reasoning_level, settings.reasoning_levels[settings.default_reasoning_level])
    # Main GGUFs vary widely in their native reasoning/chat templates. Forcing
    # synthetic <thinking> tags can consume the entire generation budget and
    # leave no visible answer. Keep reasoning levels as sampling/token controls
    # for main; reserve the legacy tagged scratchpad protocol for the small agent.
    if cfg["think"] and model == "agent":
        return base_prompt + THINK_SYSTEM_SUFFIX.format(budget=cfg["think_budget"])
    if cfg["think"] and model == "main":
        return base_prompt + (
            "\n\nReason carefully before answering, but output only the final user-visible answer. "
            "Do not emit <thinking> tags or hidden scratchpad text."
        )
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
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AsyncGenerator[str, None]:
    """Yields raw text deltas from the local model server (SSE passthrough)."""
    cfg = settings.reasoning_levels.get(reasoning_level, settings.reasoning_levels[settings.default_reasoning_level])
    url = _model_url(which)
    payload = {
        "model": _model_name(which),
        "messages": messages,
        "temperature": cfg["temperature"] if temperature is None else min(temperature, cfg["temperature"]),
        "max_tokens": max_tokens or cfg["max_tokens"],
        "stream": True,
        "cache_prompt": True,   # llama.cpp reuses the shared prompt prefix -> much faster follow-ups
        "top_k": 40,
        "repeat_penalty": 1.1,
    }
    # Many reasoning GGUF chat templates (Qwen/R1-style included) expose their
    # internal reasoning in a separate reasoning_content field instead of
    # delta.content. Ask llama.cpp to suppress that channel for the main model:
    # the UI needs the final answer, not a token budget consumed by hidden text.
    if which == "main" and reasoning_level != "off":
        payload["reasoning_format"] = "none"
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
                        choice = obj.get("choices", [{}])[0]
                        part = choice.get("delta") or {}
                        delta = part.get("content")
                        if delta:
                            yield delta
                        # Compatibility: a few llama.cpp/model-template versions put
                        # final text on choice.message at stream termination.
                        elif choice.get("finish_reason") and choice.get("message", {}).get("content"):
                            yield choice["message"]["content"]
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

async def complete(which: str, messages: list[dict], reasoning_level: str, max_tokens: Optional[int] = None) -> str:
    """Non-streaming helper. Optional token cap is useful for recovery calls."""
    chunks = []
    async for delta in stream_chat(which, messages, reasoning_level, max_tokens=max_tokens):
        if delta.startswith("__ERROR__:"):
            return ""
        chunks.append(delta)
    return "".join(chunks)

async def recover_visible_answer(which: str, user_text: str, *, context: str = "") -> str:
    """Recover from GGUF/chat-template runs that finish with no visible content.

    Keep the selected model: never silently replace Main with Fast. The retry uses
    a short direct-answer prompt and a bounded generation budget, which is more
    compatible with small local instruct/reasoning templates.
    """
    prompt = user_text[:6000]
    if context.strip():
        prompt += "\n\nRelevant context:\n" + context[-3000:]
    messages = [
        {"role": "system", "content": "Answer the user directly. Output normal visible answer text only. "
                                      "Do not output reasoning tags, analysis tags, empty content, or a preamble."},
        {"role": "user", "content": prompt},
    ]
    return (await complete(which, messages, "off", max_tokens=512)).strip()


class ThinkSplitter:
    """Incrementally splits a token stream into ("thinking", text) and
    ("answer", text) parts, correctly handling tags split across chunks."""
    OPEN, CLOSE = "<thinking>", "</thinking>"

    def __init__(self):
        self.buf = ""
        self.in_think = False

    def feed(self, text: str) -> list[tuple[str, str]]:
        self.buf += text
        out: list[tuple[str, str]] = []
        while True:
            tag = self.CLOSE if self.in_think else self.OPEN
            i = self.buf.find(tag)
            if i >= 0:
                seg = self.buf[:i]
                if seg:
                    out.append(("thinking" if self.in_think else "answer", seg))
                self.buf = self.buf[i + len(tag):]
                self.in_think = not self.in_think
                continue
            keep = 0
            for k in range(min(len(tag) - 1, len(self.buf)), 0, -1):
                if tag.startswith(self.buf[-k:]):
                    keep = k
                    break
            emit = self.buf[: len(self.buf) - keep]
            if emit:
                out.append(("thinking" if self.in_think else "answer", emit))
            self.buf = self.buf[len(self.buf) - keep:]
            return out

    def flush(self) -> list[tuple[str, str]]:
        rest, self.buf = self.buf, ""
        return [("thinking" if self.in_think else "answer", rest)] if rest else []
