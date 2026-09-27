# AI Brain — Local-First AI Learning Assistant

> A privacy-respecting, offline-capable AI assistant that runs entirely on
> your own machine: a local chat UI backed by your own GGUF models via
> `llama.cpp`, a research agent that builds a durable local knowledge base
> from trusted public sources, and a search mode that answers with cited,
> trust-ranked sources.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](backend/requirements.txt)
[![Node 18+](https://img.shields.io/badge/node-18%2B-339933.svg)](frontend/package.json)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Why this exists

Most "local AI" tooling either requires a paid API key somewhere in the
stack or quietly sends your data to a third party. This project is built
around one rule: **the system must work with zero mandatory API keys,
zero paid services, and zero data leaving your machine unless you
explicitly enable an optional integration.**

It draws a hard line between two things people often conflate:

- **Learning knowledge** — researching a topic, verifying it against
  multiple trusted sources, and storing it in a local knowledge base (the
  "AI Brain") for fast, offline retrieval.
- **Training a model** — actually changing model weights (LoRA/QLoRA).

The former happens automatically and safely. The latter is a deliberate,
explicit, user-initiated action, never a side effect.

## Features

| Area | Details |
|---|---|
| **Chat** | Streaming responses, markdown + code highlighting, copy / regenerate / fork / edit-and-resend / delete, auto-saved history (SQLite) |
| **Reasoning levels** | Off · Low · Medium · High · Max (default **Medium**) — controls sampling and an optional `<thinking>` scratchpad, shown in the UI as a live "thinking" animation |
| **Two-model architecture** | A larger model (e.g. Qwen2.5-1.5B) for chat, RAG, and synthesis; a smaller model (e.g. Qwen2.5-0.5B) for cheap agent tasks (query generation, classification, summarization) |
| **Search mode** | API-key-free web research (DuckDuckGo by default, provider-swappable), robots.txt-respecting, with a 4-tier source trust system (A: gov/edu/standards → D: forums/UGC) and a per-message "View sources" panel |
| **AI Brain** | Local, persistent knowledge store (SQLite + embeddings) that survives restarts and answers questions fully offline once populated |
| **Auto Learn** | Give it a topic; it plans subtopics, generates research questions, cross-checks multiple sources, and flags — rather than silently resolves — factual conflicts |
| **Appearance** | Dark and light themes, a settings panel for defaults |
| **Security** | Backend binds to `127.0.0.1` only, no API keys required or ever exposed to the frontend, web content is always treated as untrusted data |
| **MCP connectors** | Endpoint scaffolding in place; honestly reported as *Experimental — not yet connected* rather than faked |

See [Project status & roadmap](#project-status--roadmap) below for what's
real today versus explicitly deferred.

## Architecture

```
                         USER
                          │
                          ▼
                  React + Vite Web UI
                          │
                          ▼
                   FastAPI Backend  (127.0.0.1 only)
                          │
            ┌─────────────┼──────────────┐
            │             │              │
      Chat Engine   Research Agent   AI Brain
            │             │              │
            │      Search · Extract      │
            │      · Validate            │
            │             │              │
            └─────────────┴──────────────┘
                          │
                         RAG
                          │
                          ▼
              llama.cpp (`llama-server`)
              ├── Main model  (e.g. 1.5B) — chat, synthesis, RAG answers
              └── Agent model (e.g. 0.5B) — query gen, classification
```

## Quick start

### 1. Serve your local models with `llama.cpp`

Grab `llama-server` from the [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases)
(or build it), then run each of your GGUF models as its own server:

```bash
llama-server -m /path/to/main-model.gguf  --port 8081
llama-server -m /path/to/agent-model.gguf --port 8082
```

The backend never reads, converts, or modifies these files — it only
talks to these two local, OpenAI-compatible HTTP endpoints.

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. By default it talks only to
`http://127.0.0.1:8000`; override with `VITE_API_BASE` in a `frontend/.env`
if you changed the backend port.

## Configuration

All configuration lives in environment variables — see
[`backend/.env.example`](backend/.env.example) for the full list
(model server URLs/names, host/port, allowed CORS origins, research
throttling). Nothing sensitive is ever read from or exposed to the
frontend.

## Project status & roadmap

**Implemented and tested:** chat with streaming + full message actions,
auto-saved history, reasoning levels, dual-model routing, search mode
with trust-tiered citations, the AI Brain knowledge store, the Auto Learn
pipeline with live progress and pause/resume/cancel, dark/light themes,
and the settings panel.

**Explicitly deferred, marked Experimental in the UI rather than faked:**
MCP connector execution, file attachments in the composer, and
LoRA/QLoRA model training from exported datasets (a materially larger,
separate project from "learn knowledge first").

Contributions on any of the above are very welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please see [SECURITY.md](SECURITY.md) for supported versions and how to
report a vulnerability. In short: this app is designed to be run locally,
bound to `127.0.0.1`, with no API keys required; treat any deployment
beyond that as your own responsibility to harden.

## Contributing

Bug reports, feature requests, and pull requests are welcome. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) first, and note that this project
follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Released under the [MIT License](LICENSE).
