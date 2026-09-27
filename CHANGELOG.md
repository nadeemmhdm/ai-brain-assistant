# Changelog

All notable changes to this project are documented in this file.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed
- Upgraded `vite` (`5.4.5` → `^6.4.3`) and `@vitejs/plugin-react` (`^4.3.1` → `^4.7.0`) to
  resolve four Dependabot alerts: a Windows `server.fs.deny` bypass and a path-traversal
  issue in Vite's optimized-deps `.map` handling, an NTLMv2 hash disclosure via UNC path
  handling in `launch-editor` (no longer pulled in as a dependency), and a dev-server CORS
  issue in the bundled `esbuild` (now `0.25.x`, fixed upstream in `>=0.25.0`). All are
  dev-server-only issues (no production runtime impact); `npm audit` now reports zero
  vulnerabilities.

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

[Unreleased]: https://github.com/nadeemmhdm/ai-brain-assistant/compare/main...HEAD
