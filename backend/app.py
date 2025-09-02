from __future__ import annotations
import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from .models.api import (
    CreateSessionRequest, SessionView, EvaluateRequest, EvaluateResponse,
    ApplyActionRequest, ApplyActionResponse,
    LegalActionsResponse,
    MoveAction, AttackAction, UseSkillAction, EndTurnAction,
)
from .models.tbs import TBSSession, default_demo_mission
from .models.common import Unit, Item, Mission, StatName
from .engine.tbs_engine import TBSEngine
from .storage import Storage, InMemoryStorage
from .storage_redis import RedisStorage

# Storage: prefer Redis if REDIS_URL is set
_redis_url = os.getenv("REDIS_URL")
if _redis_url:
    import redis
    from .storage_redis import RedisStorage
    _client = redis.from_url(_redis_url, decode_responses=False)
    storage: Storage[TBSSession] = RedisStorage(client=_client, model_cls=TBSSession, key_prefix="tbs:sess")
else:
    storage = InMemoryStorage()

app = FastAPI(title="Abstract Tactics - TBS Only")
engine = TBSEngine()

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
def health() -> Dict[str, Any]:
    ok = True
    if isinstance(storage, RedisStorage):
        try:
            storage.client.ping()
            redis_connected = True
        except Exception:
            redis_connected = False
            ok = False
        health_data = {"ok": ok, "storage": "redis", "redis_connected": redis_connected}
    else:
        health_data = {"ok": ok, "storage": "memory"}
    return health_data

## Model-driven examples (avoid bespoke templates)

@app.get("/info")
def defaults_info():
    """Expose mission schema+example for session creation, plus unit/item examples used by tests."""
    demo = default_demo_mission()
    return {
        "models": {
            "unit": {"schema": Unit.model_json_schema(), "example": Unit().model_dump(mode="json")},
            "item": {"schema": Item.model_json_schema(), "example": Item().model_dump(mode="json")},
            "mission": {
                "schema": Mission.model_json_schema(),
                "example": demo.model_dump(mode="json"),
            }
        },
        "actions": {
            "move": {
                "schema": MoveAction.model_json_schema(),
                "example": MoveAction(unit_id="", to=(0, 0)).model_dump(mode="json"),
            },
            "attack": {
                "schema": AttackAction.model_json_schema(),
                "example": AttackAction(attacker_id="", target_id="").model_dump(mode="json"),
            },
            "use_skill": {
                "schema": UseSkillAction.model_json_schema(),
                "example": UseSkillAction(unit_id="", skill_id="").model_dump(mode="json"),
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

@app.post("/sessions/{sid}/evaluate", response_model=EvaluateResponse)
def evaluate_action(sid: str, req: EvaluateRequest):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    return engine.evaluate(sess, req.action)

@app.get("/sessions/{sid}/legal_actions", response_model=LegalActionsResponse)
def list_legal_actions(sid: str):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    return engine.list_legal_actions(sess)

@app.post("/sessions/{sid}/action", response_model=ApplyActionResponse)
def apply_action(sid: str, req: ApplyActionRequest):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    eval_result = engine.evaluate(sess, req.action)
    if not eval_result.legal:
        raise HTTPException(400, eval_result.explanation)
    new_state = engine.apply(sess, req.action)
    storage.save(new_state)
    return ApplyActionResponse(applied=True, explanation=eval_result.explanation,
                               session=SessionView(id=new_state.id, mission=new_state.mission))

# Serve static UI under /static (so API routes remain clean)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
