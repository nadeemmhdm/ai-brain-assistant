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
[![Landing page](https://img.shields.io/badge/landing%20page-live-d97757.svg)](https://nadeemmhdm.github.io/ai-brain-assistant/)

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
| **Assistant identity** | Default name **Nila**, friendly persona, deterministic answers to "who made you"/"your name"/"your age" (never guesses or names the underlying model), your developer's links rendered clickable |
| **Voice** | Offline speech-to-text/text-to-speech (downloaded once), full voice-to-voice mode, and a "Hey Nila" wake phrase; falls back to the browser's built-in voice with zero setup |
| **Model manager** | Import a `.gguf` you already have, load/unload models, search and download from Hugging Face (optional token for gated repos) |
| **Google integration** | Your own OAuth client for Gmail, Meet, Sheets, Slides — every action asks permission first (**this time / this chat / always / deny**) |
| **MCP connectors** | A real stdio client with a trusted starter catalog (filesystem, fetch, git, sequential-thinking) — install, discover tools, call them with your permission |
| **Skills** | Reusable saved instructions (Summarize, Explain simply, Fix grammar, Translate, Brainstorm, Code review) pick one from the composer |
| **Search mode** | API-key-free web research (DuckDuckGo by default, provider-swappable), robots.txt-respecting, with a 4-tier source trust system (A: gov/edu/standards → D: forums/UGC) and a per-message "View sources" panel |
| **AI Brain** | Local, persistent knowledge store (SQLite + embeddings) that survives restarts and answers questions fully offline once populated |
| **Auto Learn** | Give it a topic; it plans subtopics, generates research questions, cross-checks multiple sources, and flags — rather than silently resolves — factual conflicts |
| **Appearance** | Dark and light themes, a settings panel for defaults |
| **Animated, friendly UI** | Motion-powered transitions (messages, modals, nav, toasts), icon nav rail, AI Brain dashboard with search/filter, dark/light themes |
| **Training (explicit, optional)** | Build datasets from verified knowledge, review/approve examples, export JSONL, run real LoRA fine-tuning on a HuggingFace-format base model with live progress — clearly separate from Auto Learn |
| **App lock** | Optional passphrase (PBKDF2) that gates every chat-history, AI Brain, dataset and training API behind a session token |
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

**[→ View the landing page](https://nadeemmhdm.github.io/ai-brain-assistant/)**

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

### Fastest: run everything with one command

After the one-time setup below (`pip install -r backend/requirements.txt`, `npm install` in `frontend/`):

```bash
python scripts/run_dev.py     # or ./run.sh (macOS/Linux) / run.bat (Windows, double-click)
```

This starts the backend and frontend together and stops both on Ctrl+C. Your `llama-server` model processes are started separately (step 1).

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

## Google (optional)

To use the Gmail/Meet/Sheets/Slides tab:
1. In [Google Cloud Console](https://console.cloud.google.com/), create a project, then an **OAuth client ID** of type "Web application".
2. Add `http://127.0.0.1:8000/api/google/callback` as an authorised redirect URI.
3. Enable the Gmail, Calendar, Sheets, Slides and Drive APIs for the project.
4. Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `backend/.env`, then restart the backend.

Tokens are encrypted at rest and never reach the frontend. While the Cloud project is in "Testing" mode, Google expires the connection after 7 days — just reconnect from the Google tab.

## MCP connectors (optional)

The trusted starter catalog (filesystem, fetch, git, sequential-thinking) runs via `npx`, so it needs Node.js — already required for the frontend. Install one from the **MCP** tab; every tool call still asks your permission.

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
converting a trained LoRA adapter to GGUF (a manual llama.cpp step; the app tells you so rather than pretending), LoRA training itself needs the optional `backend/requirements-training.txt` and a HuggingFace-format base model (GGUF files cannot be trained directly), and conversational auto-invocation of MCP tools (today MCP tools are called manually from the MCP tab, not decided by the model mid-chat).

Contributions on any of the above are very welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

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
