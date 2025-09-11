# Abstract Tactics - TBS Game Platform

A minimal turn-based tactics platform with backend API and web UI for a Turn-Based Strategy (TBS) ruleset.

## Features

- **Web UI**: Minimal, responsive interface for game selection and play
- **API Backend**: FastAPI with async endpoints and detailed explanations
- **Game Rulesets**: TBS with extensible architecture
- **Session Management**: Redis-backed persistence (with memory fallback)
- **Docker Support**: Complete containerized setup

## Quick Start

### With Docker (Recommended)
```bash
# Build and run with auto-reload
docker compose build
PROD=false docker compose up


# 1) Start API
docker compose up -d api

# 2) Build/export (project is bind-mounted, artifacts to dist/)
docker compose run --rm godot-cs-build


# Open the web UI at http://localhost:8000
```

### Local Development
```bash
# Install dependencies
poetry install --with dev

# Start the API server
poetry run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# Open http://localhost:8000 in your browser
```

## Web UI Features

- **Game Creation**: Start new TBS games with default settings
- **Interactive Play**: Click-driven grid with move/attack/end turn
- **Session Persistence**: Save and resume games

## API Endpoints

- `GET /` - Web UI home page
- `GET /health` - Health check with storage status
- `GET /rulesets` - List available game types
- `GET /sessions` - List all game sessions
- `POST /sessions` - Create new game session
- `GET /sessions/{id}` - Get specific game session
 - `GET /sessions/{id}/legal_actions` - List pre-evaluated legal actions (use `?explain=true` for detailed breakdowns)
- `POST /sessions/{id}/action` - Apply game action

## Game Rules

### TBS (Turn-Based Strategy)
- Grid-based tactical combat
- Units with health, attack, defense, and movement
- Turn-based gameplay with action points
- Items and equipment system

## Development

```bash
# Run tests
poetry run pytest -q

# Run integration tests
poetry run pytest tests/integration/

# Format code
poetry run black .
```

## Architecture

- **Backend**: FastAPI with Pydantic models
- **Storage**: Redis for cross-worker sessions
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Games**: Plugin-based ruleset system
- **Testing**: Pytest with integration test support

## Docker Services

- **api**: FastAPI application with static file serving
- **redis**: Redis database for session storage
 - **godot-cs-build**: One-shot builder that exports a minimal Godot 4 C# desktop client (artifacts land in `dist/godot_csharp/`)

## Health Monitoring

The `/health` endpoint provides:
```json
{
  "ok": true,
  "storage": "redis",
  "redis_connected": true
}
```

## Troubleshooting

- **UI not loading**: Ensure static files are being served
- **Games not creating**: Check ruleset registration
- **Redis issues**: Verify Redis container is running
- **API errors**: Check logs with `docker compose logs api`

## Godot 4 C# Minimal Client

Build and export native binaries via Docker (no local Godot install needed):

```bash
# Exports Linux and Windows builds into dist/godot_csharp/
docker compose run --rm godot-cs-build
```

Artifacts will appear on your host:

- `dist/godot_csharp/linux/TBS-Minimal.x86_64`
- `dist/godot_csharp/windows/TBS-Minimal.exe`

Run either outside Docker. The client targets `http://localhost:8000` by default. Start the API first:

```bash
docker compose up
# or locally
poetry run uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
