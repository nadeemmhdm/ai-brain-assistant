# Contributing

Thanks for considering a contribution — this project is early-stage and
there's a lot of useful work to do, from hardening the research agent to
building out the deferred features (MCP connectors, dataset export,
LoRA/QLoRA training).

## Ground rules

- **No fake features.** If something isn't fully working, mark it
  `Experimental` or `Not configured` in the UI rather than presenting a
  mock. This is a hard project rule, not a style preference.
- **Local-first, API-key-free by default.** Core functionality must keep
  working with zero paid APIs, zero mandatory API keys, and zero data
  leaving the user's machine. Optional integrations are welcome as
  opt-in, clearly labelled additions.
- **Treat web content as untrusted.** Anything fetched from the internet
  (search results, scraped pages) must be handled as data, never as
  instructions to the agent, and never used to execute code, modify
  files, or escalate its own permissions.
- **Respect site rules.** Research/crawling code must continue to honor
  `robots.txt`, rate limits, and access restrictions — no bypassing
  CAPTCHAs, auth walls, or scraping restricted content.

## Getting set up

See the [README Quick start](README.md#quick-start) — you'll need
`llama-server` running your two GGUF models, a Python 3.10+ virtualenv
for the backend, and Node 18+ for the frontend.

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# frontend
cd frontend && npm install && npm run dev
```

## Making changes

1. Fork the repo and create a branch off `main`:
   `git checkout -b feature/short-description`
2. Keep changes focused — smaller PRs are easier to review and merge.
3. Match the existing style:
   - **Backend**: FastAPI + SQLite, type-hinted Python, one concern per
     module (`search.py`, `brain.py`, `learn.py`, etc.).
   - **Frontend**: React + TypeScript + Tailwind, components colocated by
     feature under `src/components/`, state in `src/store/useAppStore.ts`,
     all backend calls go through `src/lib/api.ts`.
4. Before opening a PR:
   ```bash
   cd frontend && npx tsc -b --noEmit && npm run build
   cd backend  && python -m py_compile app/*.py app/routers/*.py main.py
   ```
5. Describe **what** changed and **why** in the PR description, and call
   out any new environment variables, dependencies, or migrations.

## Reporting bugs / requesting features

Please use the issue templates under `.github/ISSUE_TEMPLATE/`. Include
enough detail to reproduce a bug (OS, model files used, steps, logs from
`uvicorn` and the browser console).

## Security issues

Please **do not** open a public issue for a security vulnerability — see
[SECURITY.md](SECURITY.md) for how to report one privately.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you're expected to uphold it.
