# Abstract Tactics - Chess & TBS Game Platform

A complete turn-based tactics platform with backend API and web UI for playing Chess and Turn-Based Strategy (TBS) games.

## Features

- **Web UI**: Minimal, responsive interface for game selection and play
- **API Backend**: FastAPI with async endpoints and detailed explanations
- **Game Rulesets**: Chess and TBS with extensible architecture
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

- **Game Selection**: Choose between Chess and TBS games
- **Game Creation**: Start new games with default settings
- **Interactive Play**:
  - Chess: Enter moves in algebraic notation (e.g., `e2e4`)
  - TBS: Select actions with unit/target inputs
- **Visual Boards**: Text-based game board representations
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

### Chess
- Standard chess rules with algebraic notation input
- Full game state tracking and validation

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

