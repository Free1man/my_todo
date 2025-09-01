from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.engine.session import Session
from backend.engine.store import get_session as store_get, save_session as store_set, store
from backend.core.ruleset_registry import get_ruleset, list_rulesets
from backend.core.primitives import Explanation  # for response_model typing
from backend.rulesets import *  # noqa: F401  (side-effect: registers rulesets)


app = FastAPI(title="Abstract Tactics — TBS + Chess")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)


class CreateSessionRequest(BaseModel):
    """Request to create a new game session."""
    ruleset: str
    scheduler: Optional[str] = None
    state: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check with dependency status."""
    ok = True
    storage_type = store.__class__.__name__.replace('SessionStore', '').lower()
    health_data = {"ok": ok, "storage": storage_type}
    
    if storage_type == "redis":
        try:
            await store._r.ping()  # type: ignore
            health_data["redis_connected"] = True
        except Exception:
            health_data["redis_connected"] = False
            health_data["ok"] = False
    
    return health_data


@app.get("/rulesets")
async def rulesets() -> Dict[str, Dict[str, str]]:
    # maps ruleset name -> default scheduler
    return {"rulesets": list_rulesets()}


@app.get("/sessions")
async def list_sessions() -> list[Session]:
    """List all game sessions."""
    sessions = await store.all()
    return list(sessions.values())


@app.post("/sessions", response_model=Session)
async def create_session(req: CreateSessionRequest) -> Session:
    """Create a session from a ruleset (optional initial state)."""
    rs = get_ruleset(req.ruleset)
    st = rs.create(req.state)
    sess = Session(ruleset=rs.name, scheduler=req.scheduler or rs.default_scheduler, state=st.to_serializable())
    # Best-effort summary for quick UI cards
    try:
        sess.meta.update(rs.summarize(st))
    except Exception:
        pass
    await store_set(sess)
    return sess


@app.get("/sessions/{sid}", response_model=Session)
async def read_session(sid: str) -> Session:
    """Fetch session by id with a refreshed summary."""
    s = await store_get(sid)
    if not s:
        raise HTTPException(status_code=404, detail={"ok": False, "error": "Session not found", "sid": sid})
    rs = get_ruleset(s.ruleset)
    try:
        s.meta.update(rs.summarize(rs.create(s.state)))
    except Exception:
        pass
    return s


@app.post("/sessions/{sid}/evaluate", response_model=Explanation)
async def evaluate_action(sid: str, raw: Dict[str, Any] = Body(...)) -> Explanation:
    """Dry-run an action and return a detailed Explanation."""
    s = await store_get(sid)
    if not s:
        raise HTTPException(status_code=404, detail={"ok": False, "error": "Session not found", "sid": sid})
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    return rs.evaluate(st, raw)


@app.post("/sessions/{sid}/action", response_model=Session)
async def apply_action(sid: str, raw: Dict[str, Any] = Body(...)) -> Session:
    """Apply an action to the session state; returns updated Session."""
    s = await store_get(sid)
    if not s:
        raise HTTPException(status_code=404, detail={"ok": False, "error": "Session not found", "sid": sid})
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    res = rs.apply(st, raw)
    if not res.get("ok"):
        # Bubble up structured reason for consistent client UX
        raise HTTPException(status_code=400, detail={"ok": False, "error": res.get("error", "Invalid action")})
    s.state = st.to_serializable()
    try:
        s.meta.update(rs.summarize(st))
    except Exception:
        pass
    await store_set(s)
    return s


@app.get("/rulesets/{ruleset}/info")
async def ruleset_info(ruleset: str):
    """Get schemas, templates, and examples for a ruleset."""
    rs = get_ruleset(ruleset)
    if not rs:
        raise HTTPException(status_code=404, detail="unknown ruleset")
    if not hasattr(rs, "info"):
        raise HTTPException(status_code=501, detail="ruleset doesn't expose info()")
    return rs.info(None)


@app.get("/sessions/{sid}/info")
async def session_info(sid: str):
    """Get schemas, templates, and examples for a specific session."""
    s = await store_get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    rs = get_ruleset(s.ruleset)
    if not rs or not hasattr(rs, "info"):
        raise HTTPException(status_code=400, detail="ruleset not found or no info()")
    return rs.info(rs.create(s.state))


# Mount static files (after all API routes to avoid conflicts)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
