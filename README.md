# Abstract Tactics – Commands Cheat Sheet

Minimal list of the most useful commands for daily work. (Original descriptive README replaced intentionally.)

## 1. Start / Stop Stack (Docker)
```bash
# Build images
docker compose build

# Dev run (auto-reload, not prod):
PROD=false docker compose up

# Detached
PROD=false docker compose up -d

# "Prod" flavored run (set env var or edit compose file as needed)
PROD=true docker compose up -d

# Stop
docker compose down

# Stop & remove volumes (DANGEROUS – wipes redis data)
docker compose down -v
```

## 2. File Permissions (after Docker-created files)
```bash
sudo chown -R "$(id -u)":"$(id -g)" .
```

## 3. API Local (No Docker)
```bash
poetry install --with dev
poetry run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# If VS Code is using .venv but your shell is not:
source .venv/bin/activate
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# Or without activating:
./.venv/bin/python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

## 4. Logs & Shell
```bash
# Follow API logs
docker compose logs -f api

# Open shell inside API container
docker compose exec api bash

# Redis CLI
docker compose exec redis redis-cli
```

## 5. Health & Basic API Calls
```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/rulesets | jq
curl -s http://localhost:8000/sessions | jq

# Create session (example ruleset "tbs")
curl -s -X POST http://localhost:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{"ruleset":"tbs"}' | jq

# Get legal actions
curl -s http://localhost:8000/sessions/<SESSION_ID>/legal_actions | jq

# Apply action (replace payload)
curl -s -X POST http://localhost:8000/sessions/<SESSION_ID>/action \
  -H 'Content-Type: application/json' \
  -d '{"action_type":"end_turn"}' | jq
```

## 6. Tests & Formatting
```bash
poetry run pytest -q                # All tests
poetry run pytest tests/integration # Integration only
poetry run black .                  # Format

# If poetry/pytest is not on your shell PATH, use the workspace venv directly:
./.venv/bin/python -m pytest -q tests
./.venv/bin/python -m pytest -q tests/integration

# Makefile wrappers (always use .venv/bin/python)
make test
make integration

# If the API is already running, skip Docker startup in the test fixture:
BASE_URL=http://127.0.0.1:8000 make integration
```

Integration tests also need Docker access because [`tests/integration/conftest.py`](/home/ilia/my_todo/tests/integration/conftest.py) starts or reuses the `api` and `redis` services when `BASE_URL` is not already set.

## 7. Godot C# Client Export
```bash
# Build/export desktop clients to dist/godot_csharp/
docker compose run --rm godot-cs-build

# Rebuild only that service image
docker compose build godot-cs-build
```

Artifacts go to:
- dist/godot_csharp/linux/
- dist/godot_csharp/windows/

## 8. Maintenance / Cleanup
```bash
# Clear Redis data (ALL KEYS!)
docker compose exec redis redis-cli FLUSHALL

# Remove dangling images
docker image prune -f

# Rebuild everything fresh
docker compose build --no-cache
```

## 9. Quick Troubleshooting
```bash
# Check container statuses
docker compose ps

# Verify API reachable
curl -I http://localhost:8000/health

# Permission reset (again if needed)
sudo chown -R "$(id -u)":"$(id -g)" .
```

## 10. Common Environment Variables
```bash
PROD=false   # Development defaults
PROD=true    # Production-like behavior (if referenced in code/compose)
```

## 11. One-Liners
```bash
# Start dev stack fresh
docker compose down -v && docker compose build && PROD=false docker compose up

# Run tests inside API container (if poetry installed there)
docker compose exec api poetry run pytest -q
```

---
