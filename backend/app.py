from __future__ import annotations
import os
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from .models.api import (
    CreateSessionRequest, SessionView, EvaluateRequest, EvaluateResponse,
    ApplyActionRequest, ApplyActionResponse, RulesetsView,
    LegalActionsResponse
)
from .models.tbs import TBSSession, default_demo_mission
from .models.common import MapGrid, Unit, StatBlock, Mission, StatModifier, StatName, Operation, Item
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

@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html><html><head><meta charset="utf-8"><title>TBS</title></head>
<body>
  <h1>Abstract Tactics — TBS</h1>
  <p>Open <a href="/static/index.html">/a></p>
</body></html>"""

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

@app.get("/rulesets/{ruleset}/info")
def ruleset_info(ruleset: str):
    if ruleset != "tbs":
        raise HTTPException(status_code=404, detail="unknown ruleset")
    return {
        "ruleset": "tbs",
        "models": {
            "unit": {
                "template": {
                    "id": "unit1",
                    "side": "A",
                    "name": "Warrior",
                    "strength": 3,
                    "defense": 1,
                    "max_hp": 10,
                    "hp": 10,
                    "max_ap": 2,
                    "ap": 2,
                    "pos": {"x": 0, "y": 0},
                    "item_ids": []
                }
            },
            "item": {
                "template": {
                    "id": "item1",
                    "name": "Basic Item",
                    "attack_bonus": 0,
                    "defense_bonus": 0,
                    "range_bonus": 0
                }
            }
        },
        "actions": {
            "attack": {
                "template": {"type": "attack", "attacker_id": "", "target_id": ""}
            },
            "move": {
                "template": {"type": "move", "unit_id": "", "to": {"x": 0, "y": 0}}
            },
            "end_turn": {
                "template": {"type": "end_turn"}
            }
        }
    }

@app.get("/sessions/{sid}/info")
def session_info(sid: str):
    sess = storage.get(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "actions": {
            "attack": {"template": {"type": "attack", "attacker_id": "", "target_id": ""}},
            "move": {"template": {"type": "move", "unit_id": "", "to": {"x": 0, "y": 0}}},
            "end_turn": {"template": {"type": "end_turn"}}
        }
    }

@app.get("/rulesets", response_model=RulesetsView)
def get_rulesets():
    return RulesetsView(rulesets=["tbs"])

@app.get("/sessions", response_model=list[SessionView])
def list_sessions():
    return [SessionView(id=s.id, mission=s.mission) for s in storage.list_all()]

@app.post("/sessions", response_model=SessionView)
def create_session(req: CreateSessionRequest):
    if req.state:
        # Convert old state to Mission
        map_data = req.state.get("map", {})
        width = map_data.get("width", 8)
        height = map_data.get("height", 8)
        obstacles = map_data.get("obstacles", [])
        tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                terrain = "BLOCKED" if {"x": x, "y": y} in obstacles else "PLAIN"
                row.append({"terrain": terrain, "mods": []})
            tiles.append(row)
        grid = MapGrid(width=width, height=height, tiles=tiles)
        items = {}
        for iid, it in req.state.get("items", {}).items():
            mods = []
            if it.get("attack_bonus"):
                mods.append(StatModifier(stat=StatName.ATK, operation=Operation.ADDITIVE, value=it["attack_bonus"]))
            if it.get("defense_bonus"):
                mods.append(StatModifier(stat=StatName.DEF, operation=Operation.ADDITIVE, value=it["defense_bonus"]))
            if it.get("range_bonus"):
                mods.append(StatModifier(stat=StatName.RNG, operation=Operation.ADDITIVE, value=it["range_bonus"]))
            items[iid] = Item(id=iid, name=it["name"], mods=mods)

        units = {}
        for uid, u in req.state.get("units", {}).items():
            side = "PLAYER" if u["side"] == "A" else "ENEMY"
            item_ids = u.get("item_ids", [])
            unit_items = [items[iid] for iid in item_ids if iid in items]
            unit = Unit(
                id=u["id"],
                side=side,
                name=u["name"],
                pos=(u["pos"]["x"], u["pos"]["y"]),
                stats=StatBlock(base={
                    "HP": u["hp"],
                    "AP": u["ap"],
                    "ATK": u["strength"],
                    "DEF": u["defense"],
                    "MOV": 4,
                    "RNG": 1,
                    "CRIT": 5
                }),
                items=unit_items,
                injuries=[],
                auras=[],
                skills=[],
                alive=u["hp"] > 0,
                ap_left=u["ap"]
            )
            units[uid] = unit
        active_side = "PLAYER" if req.state.get("active_side") == "A" else "ENEMY"
        mission = Mission(
            id="m.custom",
            name="Custom",
            map=grid,
            units=units,
            side_to_move=active_side,
            turn=req.state.get("turn_number", 1),
            goals=[],
            pre_events=[],
            post_events=[],
            global_mods=[],
            current_unit_id=req.state.get("turn_order", [None])[req.state.get("active_index", 0)] if req.state.get("turn_order") else None,
            unit_order=req.state.get("turn_order", []),
            current_unit_index=req.state.get("active_index", 0)
        )
    else:
        mission = req.mission or default_demo_mission()
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

app.mount("/", StaticFiles(directory="static", html=True), name="static")
