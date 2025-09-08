from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import storage
from .engine.auto_enemy import enemy_autoplay
from .engine.core import TBSEngine
from .logging_listeners import register_listeners
from .missions.demo import default_demo_mission
from .models.api import (
    ActionLogEntry,
    ActionLogResponse,
    ApplyActionRequest,
    ApplyActionResponse,
    AttackAction,
    CreateSessionRequest,
    EndTurnAction,
    LegalActionsResponse,
    MoveAction,
    SessionView,
    UseSkillAction,
)
from .models.mission import Mission
from .models.session import TBSSession
from .models.skills import Item
from .models.units import Unit

app = FastAPI(title="Abstract Tactics - TBS Only")
engine = TBSEngine()
register_listeners()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index():
    return RedirectResponse(url="/static/index.html", status_code=307)


@app.get("/health")
def health() -> dict[str, Any]:
    ok = True
    try:
        storage.r.ping()
        redis_connected = True
    except Exception:
        redis_connected = False
        ok = False
    return {"ok": ok, "storage": "redis", "redis_connected": redis_connected}


## Model-driven examples (avoid bespoke templates)


@app.get("/info")
def defaults_info():
    """Expose mission schema+example for session creation, plus unit/item examples used by tests."""
    demo = default_demo_mission()
    return {
        "models": {
            "unit": {
                "schema": Unit.model_json_schema(),
                "example": Unit().model_dump(mode="json"),
            },
            "item": {
                "schema": Item.model_json_schema(),
                "example": Item().model_dump(mode="json"),
            },
            "mission": {
                "schema": Mission.model_json_schema(),
                "example": demo.model_dump(mode="json"),
            },
        },
        "actions": {
            "move": {
                "schema": MoveAction.model_json_schema(),
                "example": MoveAction(unit_id="", to=(0, 0)).model_dump(mode="json"),
            },
            "attack": {
                "schema": AttackAction.model_json_schema(),
                "example": AttackAction(attacker_id="", target_id="").model_dump(
                    mode="json"
                ),
            },
            "use_skill": {
                "schema": UseSkillAction.model_json_schema(),
                "example": UseSkillAction(unit_id="", skill_id="").model_dump(
                    mode="json"
                ),
            },
            "end_turn": {
                "schema": EndTurnAction.model_json_schema(),
                "example": EndTurnAction().model_dump(mode="json"),
            },
        },
        "requests": {
            "create_session": {
                "schema": CreateSessionRequest.model_json_schema(),
                "example": {"mission": demo.model_dump(mode="json")},
            }
        },
    }


@app.get("/sessions", response_model=list[SessionView])
def list_sessions():
    return [SessionView(id=s.id, mission=s.mission) for s in storage.list_all()]


@app.post("/sessions", response_model=SessionView)
def create_session(req: CreateSessionRequest):
    mission = req.mission or default_demo_mission()
    # Initialize dynamic initiative order and AP using engine's public API
    engine.initialize_mission(mission)
    sid = str(uuid4())
    sess = TBSSession(id=sid, mission=mission)
    storage.save(sess)
    return SessionView(id=sess.id, mission=sess.mission)


@app.get("/sessions/{sid}", response_model=SessionView)
def get_session(sid: str):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    return SessionView(id=sess.id, mission=sess.mission)


@app.get("/sessions/{sid}/legal_actions", response_model=LegalActionsResponse)
def list_legal_actions(sid: str, explain: bool = False):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    return engine.list_legal_actions(sess, explain=explain)


@app.post("/sessions/{sid}/action", response_model=ApplyActionResponse)
def apply_action(sid: str, req: ApplyActionRequest):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    eval_result, new_state = engine.process_action(sess, req.action)
    if not eval_result.legal:
        raise HTTPException(400, eval_result.explanation)
    # Auto-enemy: apply a few enemy actions if enabled on the mission
    if new_state.mission.enemy_ai:
        applied, after = enemy_autoplay(engine, new_state)
        new_state = after
    new_state.mission.status = engine.check_victory_conditions(new_state)
    # Applied action already logged inside engine.apply

    storage.save(new_state)
    return ApplyActionResponse(
        applied=True,
        explanation=eval_result.explanation,
        session=SessionView(id=new_state.id, mission=new_state.mission),
    )


# Serve static UI under /static (so API routes remain clean)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/sessions/{sid}/log", response_model=ActionLogResponse)
def get_action_log(sid: str, limit: int = Query(50, ge=1, le=1000)):
    # basic existence check
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    try:
        raw = storage.logs.list(sid, limit)
    except Exception:
        raw = []
    entries: list[ActionLogEntry] = []
    from pydantic import TypeAdapter

    # Validate each stored JSON string as a single ActionLogEntry
    ta = TypeAdapter(ActionLogEntry)
    for s in raw:
        try:
            entries.append(ta.validate_json(s))
        except Exception:
            # Skip malformed entries rather than failing the whole response
            continue

    return ActionLogResponse(entries=entries)
