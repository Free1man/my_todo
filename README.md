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

# The container listens on 8000, and Docker will pick a free host port.
# Find the mapped host port:
docker compose port api 8000
# Example output: 0.0.0.0:49153
# Then open http://localhost:<that_port>/docs
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

Assuming the app is running via Docker Compose. First, capture the host port:

```bash
HOSTPORT=$(docker compose port api 8000 | sed 's/.*://')
echo "$HOSTPORT"
```

```bash
# Health check
curl http://localhost:${HOSTPORT}/health

# If curl isn't installed on your host, run it inside the container (container port is 8000):
docker compose exec -T api curl http://localhost:8000/health

# Register a user (returns 201)
curl -X POST http://localhost:${HOSTPORT}/register \
	-H 'Content-Type: application/json' \
	-d '{"username":"alice","password":"secret"}'

# Login to get a token
# Option A (with jq):
# TOKEN=$(curl -s -X POST http://localhost:${HOSTPORT}/login -H 'Content-Type: application/json' -d '{"username":"alice","password":"secret"}' | jq -r .access_token)
# Option B (no jq): naive sed extraction
TOKEN=$(curl -s -X POST http://localhost:${HOSTPORT}/login \
	-H 'Content-Type: application/json' \
	-d '{"username":"alice","password":"secret"}' | sed -E 's/.*"access_token"\s*:\s*"([^"]+)".*/\1/')
echo "$TOKEN"

# List todos (empty at first)
curl http://localhost:${HOSTPORT}/todos \
	-H "Authorization: Bearer $TOKEN"

# Create a todo
curl -X POST http://localhost:${HOSTPORT}/todos \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $TOKEN" \
	-d '{"text":"buy milk"}'

# Update a todo (replace <id>)
curl -X PATCH http://localhost:${HOSTPORT}/todos/<id> \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $TOKEN" \
	-d '{"done":true}'

# Delete a todo
curl -X DELETE http://localhost:${HOSTPORT}/todos/<id> \
	-H "Authorization: Bearer $TOKEN" -i

# Status-only health check (200 when healthy)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:${HOSTPORT}/health
```

## Dev Container (VS Code)

1. Install **Dev Containers** extension.
2. Open this folder in VS Code → **Reopen in Container**.
3. Run the app: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
	- Dev Containers will auto-forward port 8000 for you, no host publish is required.

## Swap CSV for a DB later

All file I/O is isolated in `app/storage.py`. Replace implementations there.
