# tests/integration/utils/helpers.py
import json
import requests
from backend.models.api import AttackAction
from backend.models.common import Mission, Unit, StatName, MapGrid, Tile, Terrain, Side, GoalKind, MissionGoal

# ---------- HTTP helpers (show server error bodies) ----------
def _post(url: str, payload: dict, *, timeout=5) -> dict:
    r = requests.post(url, json=payload, timeout=timeout)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        raise requests.HTTPError(
            f"{r.status_code} {r.reason} for {url}\n"
            f"Payload:\n{json.dumps(payload, indent=2)}\n"
            f"Response:\n{body}",
            response=r,
        )
    return r.json()

def _get(url: str, *, timeout=5) -> dict:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _session_get(base_url: str, sid: str) -> dict:
    return _get(f"{base_url}/sessions/{sid}")

# ---------- verify/create helpers ----------
def _units_by_id(sess_json: dict) -> dict[str, dict]:
    units = sess_json.get("mission", {}).get("units", {})
    return units

def _hp_of(sess_json: dict, uid: str) -> int:
    u = _units_by_id(sess_json)[uid]
    # In the new model, stats are nested
    return u["stats"]["base"]["HP"]

def _create_tbs_session(base_url: str, mission: Mission) -> tuple[str, dict]:
    """Create a TBS session using a typed Mission object."""
    desired_ids = set(mission.units.keys())
    # Pydantic model_dump_json -> json string -> json.loads -> dict
    body = {"mission": json.loads(mission.model_dump_json(exclude_none=True))}

    sess = _post(f"{base_url}/sessions", body)
    sid = sess["id"]

    # fetch authoritative state after create
    sess = _get(f"{base_url}/sessions/{sid}")
    present_ids = set(_units_by_id(sess).keys())

    # sanity check: ensure server actually used our state
    if desired_ids and not desired_ids.issubset(present_ids):
        raise AssertionError(
            "Server did not accept the custom TBS Mission.\n"
            f"Wanted unit IDs: {sorted(desired_ids)}\n"
            f"Got unit IDs:    {sorted(present_ids)}\n"
            "The backend may be using a default mission instead of the provided one."
        )

    return sid, sess

def _evaluate(base_url: str, sid: str, payload: dict) -> dict:
    return _post(f"{base_url}/sessions/{sid}/evaluate", {"action": payload})

def _apply(base_url: str, sid: str, payload: dict) -> dict:
    _post(f"{base_url}/sessions/{sid}/action", {"action": payload})
    # Always re-fetch so we assert against the stored state, not a handler echo
    return _session_get(base_url, sid)
