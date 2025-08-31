from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.engine.session import Session
from backend.engine.store import SESSIONS
from backend.core.ruleset_registry import get_ruleset, list_rulesets
from backend.rulesets import *  # noqa: F401  (side-effect: registers rulesets)

app = FastAPI(title="Abstract Tactics — TBS + Chess")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class CreateSessionRequest(BaseModel):
    ruleset: str
    scheduler: Optional[str] = None
    state: Optional[Dict[str, Any]] = None


@app.get("/health")
def health(): return {"ok": True}


@app.get("/rulesets")
def rulesets(): return {"rulesets": list_rulesets()}


@app.post("/sessions", response_model=Session)
def create_session(req: CreateSessionRequest):
    rs = get_ruleset(req.ruleset)
    st = rs.create(req.state)
    sess = Session(ruleset=rs.name, scheduler=req.scheduler or rs.default_scheduler, state=st.to_serializable())
    try: sess.meta.update(rs.summarize(st))
    except Exception: pass
    SESSIONS[sess.id] = sess
    return sess


@app.get("/sessions/{sid}", response_model=Session)
def get_session(sid: str):
    s = SESSIONS.get(sid) or (_ for _ in ()).throw(HTTPException(404, "Session not found"))
    rs = get_ruleset(s.ruleset)
    try: s.meta.update(rs.summarize(rs.create(s.state)))
    except Exception: pass
    return s


@app.post("/sessions/{sid}/evaluate")
def evaluate_action(sid: str, raw: Dict[str, Any] = Body(...)):
    s = SESSIONS.get(sid) or (_ for _ in ()).throw(HTTPException(404, "Session not found"))
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    return rs.evaluate(st, raw).model_dump()


@app.post("/sessions/{sid}/action", response_model=Session)
def apply_action(sid: str, raw: Dict[str, Any] = Body(...)):
    s = SESSIONS.get(sid) or (_ for _ in ()).throw(HTTPException(404, "Session not found"))
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    res = rs.apply(st, raw)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "Invalid action"))
    s.state = st.to_serializable()
    try: s.meta.update(rs.summarize(st))
    except Exception: pass
    return s
