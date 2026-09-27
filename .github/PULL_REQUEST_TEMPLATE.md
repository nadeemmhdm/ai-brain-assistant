## Summary

<!-- What does this PR change, and why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / chore

## Checklist

- [ ] `cd frontend && npx tsc -b --noEmit && npm run build` passes
- [ ] `cd backend && python -m py_compile app/*.py app/routers/*.py main.py` passes
- [ ] New/changed env vars are documented in `backend/.env.example` and the README
- [ ] No mandatory API key or paid service was introduced
- [ ] Any unfinished feature is clearly marked `Experimental` / `Not configured` in the UI, not faked
- [ ] Web-fetched content is still treated as untrusted data, not instructions

## Screenshots (if UI change)

<!-- Before/after screenshots or a short clip help a lot. -->
