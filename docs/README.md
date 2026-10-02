# AI Brain Documentation

This folder is the canonical home for project documentation published with the AI Brain landing page.

## Documents

- [Error Codes](ERROR_CODES.md) — stable error identifiers, meanings, recovery hints and API format.
- [Private Cloud Training](CLOUD_TRAINING.md) — single-provider cloud teacher setup, CLI usage and privacy boundary.
- [Main README](../README.md) — installation, features, CLI, Trusted Topic Learning and development overview.
- [Security](../SECURITY.md) — vulnerability reporting and security policy.
- [Contributing](../CONTRIBUTING.md) — contribution workflow and development guidance.

## Error-code convention

Runtime errors should use the centralized registry in `backend/app/errors.py`. New codes must be documented in `ERROR_CODES.md` and added to the landing-page search index. Existing codes should not be silently reused for a different meaning.

## Documentation convention

New technical documentation should be written as Markdown and placed in `docs/`. Keep README concise and link detailed guides from this index.
