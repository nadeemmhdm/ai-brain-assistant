# Security Policy

## Design principles

This project is built to run **locally, on a single machine, bound to
`127.0.0.1`**. That design choice is itself a security control:

- The backend does not bind to `0.0.0.0` or accept remote connections by
  default (`BACKEND_HOST` in `.env`).
- No API keys are required for core functionality, and none are ever sent
  to or stored in the frontend — the browser only ever talks to your own
  local backend.
- Content fetched from the web during research (Search mode / Auto Learn)
  is always treated as **untrusted data**, never as instructions. It is
  labelled and passed to the model as context; nothing in a fetched page
  can make the agent execute commands, modify files, or change its own
  behavior.
- The research agent respects `robots.txt`, applies rate limiting, and
  will not bypass access controls or scrape authenticated/private content.
- Optional third-party integrations (embedding models, MCP connectors,
  future search providers) are opt-in and off by default.

## Supported versions

This project is under active development (pre-1.0). Only the latest
commit on `main` is supported with security fixes.

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| Older commits/tags | ❌ |

## Reporting a vulnerability

If you find a security issue (e.g. a way to escape the local-only
binding, achieve remote code execution via crafted web content, exfiltrate
local data through a search/Auto Learn request, or bypass the
robots.txt/rate-limiting protections), please report it privately rather
than opening a public issue:

1. Open a [GitHub Security Advisory](../../security/advisories/new) on
   this repository ("Report a vulnerability"), **or**
2. If that's not available, open a regular issue titled `SECURITY:` with
   only a short summary and a request for a private channel — do not
   post exploit details publicly.

Please include:
- A clear description of the issue and its impact
- Steps to reproduce (a minimal example is ideal)
- The commit/version you tested against

We aim to acknowledge reports within a few days and to publish a fix or
mitigation as soon as reasonably possible. Please allow time for a fix
before any public disclosure.

## Out of scope

- Vulnerabilities that require the attacker to already have local access
  to the machine running the backend (the threat model assumes a
  single-user, single-machine deployment).
- Issues in third-party dependencies (`llama.cpp`, DuckDuckGo, etc.) —
  please report those upstream, though a note here linking to the report
  is welcome.
