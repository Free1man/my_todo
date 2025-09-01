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
- `POST /sessions/{id}/evaluate` - Dry-run action with explanation
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

