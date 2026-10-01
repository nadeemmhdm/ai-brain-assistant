# Changelog

All notable changes to this project are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/),
and this project uses [Semantic Versioning](https://semver.org/) (pre-1.0,
so breaking changes may still happen between minor versions).

## [Unreleased]

## [0.5.0-beta.1] - 2026-09-30

### Fixed
- **No visible reply at high reasoning levels**: a small model could spend its entire token budget inside `<thinking>` and never close the tag, leaving the chat bubble empty. The backend now does a quick, tagless follow-up call to force an actual answer whenever this happens, raised the token ceilings for High/Max reasoning, and made the thinking-budget instruction more insistent about wrapping up in time.
- **General-knowledge questions mistaken for identity questions**: asking things like "who founded OpenAI" could trigger the assistant's "I don't share technical details about myself" deflection. The identity rule is now scoped explicitly to questions about the assistant itself; ordinary world-knowledge questions (including about other AI systems) are answered normally.
- **Over-cautious refusals on legitimate technical/security topics**: questions like "what is vulnerability scanning" could get a generic "as an AI I don't have access to that" non-answer. The persona and Auto Learn prompts now explicitly treat cybersecurity, networking, and other technical subjects as ordinary educational topics to answer directly (still declining real operational attack instructions against a specific system).
- **Unhelpful error messages**: backend errors (e.g. Auto Learn's "already running" conflict) were shown to the user as a bare `"409 Conflict"` instead of the actual explanation — the frontend now surfaces the real error text everywhere.
- **Auto Learn 409 with no way forward**: opening the Auto Learn dialog now checks for and resumes an already-running session instead of just failing to start a second one.

### Added
- **Real offline translation** for the Translate skill, via **Argos Translate** (the open-source engine LibreTranslate is also built on) — install a language pack once (Models tab → Translate), then translation runs fully offline with no LLM guessing involved. Say "to French: hello there" in the composer with the Translate skill selected.
- **Message waiting list**: you can now type and send while a reply is still generating — up to 5 messages queue up, shown above the composer, and send automatically in order once the current reply finishes. Each queued message can be edited, sent immediately (jumping the queue), or removed.
- **Collapsible sidebar**: a toggle in the top bar hides/shows the chat sidebar, animated, with the state remembered between sessions.
- 4 more trusted MCP servers in the starter catalog: Memory, Time, SQLite, and the official Everything test server.
- 6 more built-in Skills: Make concise, Debug this, Action items, Pros and cons, Mock interviewer, Write tests.
- Quick search now reads 3–5 sources and Deep search 5–7 (previously capped at 3 for both).
- Expanded trusted-source list with cybersecurity authorities (NVD, MITRE CVE/CWE/ATT&CK, CISA, FIRST.org) and more established references (Stack Overflow, GitHub, PortSwigger, Exploit-DB) for better-grounded technical answers.
- Lowered the default local context window to 4096 tokens for smoother performance on 8GB-RAM machines (raise `LLAMA_CTX` in `.env` if you have more memory).

### Added
- Landing page for GitHub Pages (`docs/index.html`): responsive, dark/terracotta theme matching the app, a typed-out terminal hero, an animated architecture diagram, a 3-line mobile hamburger menu, and live GitHub star/release badges fetched client-side.

## [0.4.0-beta.1] - 2026-09-29

### Fixed
- **Message ordering bug**: the assistant's (empty) reply could render above the user's own message until a refresh — the user's message is now appended optimistically before the request is sent, instead of waiting for the server's echo.
- **Search mode fabricating answers**: when web search returned nothing useful, the model would still answer as if grounded, sometimes producing literal `[Name]`/`[Year]`-style placeholder text. Added a standing instruction never to output placeholder-style guesses, softened the grounding prompt so irrelevant search context is ignored instead of confusing the model, and skip search entirely for arithmetic/greetings that plainly don't need it.
- **Silent DuckDuckGo failures**: search errors are now raised and surfaced to the user as a clear status notice instead of silently producing an empty, ungrounded answer. Switched to the actively maintained `ddgs` package (successor to `duckduckgo-search`) with a hardened HTML fallback.
- **Auto Learn doing nothing on click**: the start button now shows a loading state and surfaces backend errors (e.g. a session already running, empty topic) instead of failing silently; the backend endpoint validates input and returns clear error messages.

### Added
- **Assistant identity**: default name **Nila**, friendly/professional persona, a set date of birth (2 Feb 2026) with an automatic birthday message, and deterministic answers to "who made you"/"your name"/"your age"/"your links" questions (never guesses, never names the underlying model or company) — developer credit and clickable GitHub/Instagram links.
- **Onboarding**: first-run screen asking what to call the assistant and what it should call you.
- **Voice**: offline speech-to-text (faster-whisper) and text-to-speech (Piper), downloaded once from Settings → Voice, with a full voice-to-voice conversation mode; falls back to the browser's built-in speech APIs when local voice isn't set up. A "Hey Nila" wake-phrase listener (tolerant of mis-hearings) can start a voice turn hands-free.
- **Model manager**: import a `.gguf` you already have (in place or copied in), load/unload the main and agent roles, search and download models from Hugging Face (with an optional, encrypted access token for gated repos), and a live downloads panel.
- **Google integration**: your own OAuth client (PKCE, tokens encrypted at rest) for Gmail (read/draft/send/trash), Google Meet (create/list/update/share/delete, with invite links), Sheets and Slides — every action requires explicit permission (**Allow this time / this chat / always / deny**) surfaced both inline in chat and in a dedicated Google tab.
- **Smarter chat pipeline**: streamed `<thinking>` reasoning shown live and separately from the answer, rolling conversation summarization so long chats keep working, real conversation forking, auto-generated chat titles, a confidence badge on researched answers, and a check that flags numbers/years the sources don't actually support.
- **Manual + automatic Brain training**: teach a fact directly, import a text file, and a watch-list of topics that re-research themselves on a schedule when the app is online and idle.
- **Optional self-update**: checks GitHub releases and can fast-forward a git checkout to the latest tagged release on request (or automatically, if opted in).
- Real MCP connector support: a stdio JSON-RPC client, a trusted starter catalog (filesystem, fetch, git, sequential-thinking — official `@modelcontextprotocol` servers, no extra credentials needed), install/start/stop, tool discovery, and a permission-gated manual tool-call UI. Custom servers can be added too, clearly marked as not pre-vetted.
- **Skills**: reusable saved instructions (Summarize, Explain simply, Fix grammar, Translate, Brainstorm, Code review ship by default) pickable from the composer and applied to a single message; users can add/edit their own.
- Answer links render as clickable text throughout (confirmed via the existing Markdown renderer).

## [0.2.0-beta.1] - 2026-09-28

### Added
- Motion-based animations throughout (message entrance, modals, nav pill, toasts, progress bars, lock screen).
- Icon nav rail with new **AI Brain** dashboard (stats, search, topic filter, delete, learning history) and **Training** view.
- Dataset generation from verified knowledge, per-example approve/reject, JSONL export.
- Real LoRA fine-tuning job runner (lazy-imported torch/peft; optional `requirements-training.txt`) with live progress; clear notes that GGUF cannot be trained and conversion is a manual llama.cpp step.
- Optional passphrase app-lock protecting chats, AI Brain, datasets and training APIs (PBKDF2 + session tokens).
- One-command launcher: `python scripts/run_dev.py`, `run.sh`, `run.bat`.
- Toast notifications.

## [0.1.0-beta.1] - 2026-09-27

First public beta. Functional local-first AI assistant with a working
chat UI, local dual-model routing, search mode, an offline AI Brain, and
an Auto Learn research pipeline. See the README's "Project status &
roadmap" section for what's fully implemented versus marked Experimental.

### Added
- Initial local-first AI assistant: FastAPI backend + React/Vite/Tailwind frontend.
- Dual-model routing to local `llama-server` instances (main + agent models).
- Reasoning levels (Off/Low/Medium/High/Max, default Medium) with `<thinking>` scratchpad support.
- Chat: streaming, markdown rendering, copy / regenerate / fork / edit-and-resend / delete, auto-saved SQLite history.
- Search mode: DuckDuckGo-based research with robots.txt-respecting fetch, 4-tier source trust classification, and a per-message sources drawer.
- AI Brain: local knowledge store with embeddings (sentence-transformers optional, hashed fallback by default).
- Auto Learn pipeline: topic → subtopics → questions → multi-source research → verified/conflicted knowledge, with live progress and pause/resume/cancel.
- Dark/light themes and a settings panel.
- Honest `Experimental` placeholders for MCP connectors and file attachments; LoRA/QLoRA training deferred entirely.
- Project governance: README, SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, MIT LICENSE, issue/PR templates.
- A `main-branch-protection` ruleset: no force-push, no deletion, linear history, PR required (admin bypass retained).

### Fixed
- Upgraded `vite` (`5.4.5` → `^6.4.3`) and `@vitejs/plugin-react` (`^4.3.1` → `^4.7.0`) to
  resolve four Dependabot alerts: a Windows `server.fs.deny` bypass and a path-traversal
  issue in Vite's optimized-deps `.map` handling, an NTLMv2 hash disclosure via UNC path
  handling in `launch-editor` (no longer pulled in as a dependency), and a dev-server CORS
  issue in the bundled `esbuild` (now `0.25.x`, fixed upstream in `>=0.25.0`). All were
  dev-server-only issues (no production runtime impact); `npm audit` now reports zero
  vulnerabilities.

[Unreleased]: https://github.com/nadeemmhdm/ai-brain-assistant/compare/v0.5.0-beta.1...HEAD
[0.5.0-beta.1]: https://github.com/nadeemmhdm/ai-brain-assistant/compare/v0.4.0-beta.1...v0.5.0-beta.1
[0.4.0-beta.1]: https://github.com/nadeemmhdm/ai-brain-assistant/compare/v0.2.0-beta.1...v0.4.0-beta.1
[0.2.0-beta.1]: https://github.com/nadeemmhdm/ai-brain-assistant/compare/v0.1.0-beta.1...v0.2.0-beta.1
[0.1.0-beta.1]: https://github.com/nadeemmhdm/ai-brain-assistant/releases/tag/v0.1.0-beta.1
