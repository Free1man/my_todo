# Abstract Tactics Backend (TBS + Chess)

A small, ruleset-agnostic turn-based tactics backend with two plug-ins: Generic TBS and Chess. The FastAPI app is exposed at `backend.app:app`.

- API: evaluate/apply with detailed explanations
- Rulesets: `tbs` and `chess` auto-registered
- Docker: compose/Dockerfile intact; health at `/health`

## Quick start (Docker)

```bash
# Build and run (PROD=false enables auto-reload)
docker compose build
PROD=false docker compose up

# Open http://localhost:8000/health
```

## Endpoints

- GET /health → { ok: true }
- GET /rulesets → list of registered rulesets
- POST /sessions → { ruleset: "tbs"|"chess", seed?: int } → creates a session
- GET /sessions/{id} → session snapshot
- POST /sessions/{id}/evaluate → { action, payload } → returns Explanation
- POST /sessions/{id}/action → { action, payload } → applies action

## Develop & test

```bash
poetry install --with dev
poetry run pytest -q
```

