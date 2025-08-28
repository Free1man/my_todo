# Tiny TODO API

## Testing

This repo includes pytest-based integration tests that spin up the FastAPI server (uvicorn), then concurrently register 10 users and create/finish 100 todos per user using threads.

Install and run with Poetry:

```
poetry install --with dev
poetry run pytest -q
```

# Tiny TODO API (FastAPI + CSV)

A super-simple local TODO backend with user registration & JWT auth.

- **Storage:** CSV files (users & todos) in `./data` (easy to swap later)
- **API:** FastAPI with JWT (PyJWT) + password hashing (passlib[bcrypt])
- **Dev:** VS Code Dev Containers
- **Run:** Docker Compose

## Quick start (Docker)

```bash
# 1) Optional: set secrets/env
# If you want a custom secret, create a .env file and set SECRET_KEY
# echo 'SECRET_KEY=change-me' > .env

# 2) Build & run
docker compose up --build

# The app is available at http://localhost:8000 (ports are mapped in docker-compose).
# Open the interactive docs:
# http://localhost:8000/docs
```

## Develop locally with Poetry

```bash
# Install Poetry if needed: https://python-poetry.org/docs/#installation
poetry install --no-root

# Run the app
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

- `POST /register` — body: `{"username":"alice","password":"******"}`
- `POST /login` — body: `{"username":"alice","password":"******"}` → returns access token
- `GET /todos` — list current user's todos
- `POST /todos` — body: `{"text":"buy milk"}`
- `PATCH /todos/{id}` — body: `{"done": true}`
- `DELETE /todos/{id}`

All `/todos*` require `Authorization: Bearer <token>` from `/login`.

## Try it with curl

Assuming the app is running via Docker Compose on http://localhost:8000.

```bash
# Health check
curl http://localhost:8000/health

# If curl isn't installed on your host, run it inside the container (container port is 8000):
docker compose exec -T api curl http://localhost:8000/health

# Register a user (returns 201)
curl -X POST http://localhost:8000/register \
	-H 'Content-Type: application/json' \
	-d '{"username":"alice","password":"secret"}'

# Login to get a token
# Option A (with jq):
# TOKEN=$(curl -s -X POST http://localhost:8000/login -H 'Content-Type: application/json' -d '{"username":"alice","password":"secret"}' | jq -r .access_token)
# Option B (no jq): naive sed extraction
TOKEN=$(curl -s -X POST http://localhost:8000/login \
	-H 'Content-Type: application/json' \
	-d '{"username":"alice","password":"secret"}' | sed -E 's/.*"access_token"\s*:\s*"([^"]+)".*/\1/')
echo "$TOKEN"

# List todos (empty at first)
curl http://localhost:8000/todos \
	-H "Authorization: Bearer $TOKEN"

# Create a todo
curl -X POST http://localhost:8000/todos \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $TOKEN" \
	-d '{"text":"buy milk"}'

# Update a todo (replace <id>)
curl -X PATCH http://localhost:8000/todos/<id> \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $TOKEN" \
	-d '{"done":true}'

# Delete a todo
curl -X DELETE http://localhost:8000/todos/<id> \
	-H "Authorization: Bearer $TOKEN" -i

# Status-only health check (200 when healthy)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
```

## Dev Container (VS Code)

1. Install **Dev Containers** extension.
2. Open this folder in VS Code → **Reopen in Container**.
3. Run the app: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
	- Dev Containers will auto-forward port 8000 for you, no host publish is required.

## Swap CSV for a DB later

All file I/O is isolated in `app/storage.py`. Replace implementations there.
