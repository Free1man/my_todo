# tests/integration/test_api_tbs.py
import copy
import json
import pytest
import requests

# Build a Mission payload (new typed API) from the lightweight state dict used in tests
def _mission_from_state(info: dict, state: dict) -> dict:
    width = state["map"]["width"]
    height = state["map"]["height"]
    # tiles: default PLAIN with optional BLOCKED from obstacles
    obstacles = { (o["x"], o["y"]) for o in state["map"].get("obstacles", []) }
    tiles = [[{"terrain": ("BLOCKED" if (x, y) in obstacles else "PLAIN"), "mods": []}
              for x in range(width)] for y in range(height)]

    # items
    items = {}
    for iid, it in (state.get("items") or {}).items():
        mods = []
        if it.get("attack_bonus"):
            mods.append({"stat": "ATK", "operation": "ADDITIVE", "value": it["attack_bonus"]})
        if it.get("defense_bonus"):
            mods.append({"stat": "DEF", "operation": "ADDITIVE", "value": it["defense_bonus"]})
        if it.get("range_bonus"):
            mods.append({"stat": "RNG", "operation": "ADDITIVE", "value": it["range_bonus"]})
        items[iid] = {"id": iid, "name": it.get("name", iid), "mods": mods}

    # units
    units = {}
    for uid, u in (state.get("units") or {}).items():
        units[uid] = {
            "id": uid,
            "side": ("PLAYER" if u.get("side") == "A" else "ENEMY"),
            "name": u.get("name", uid),
            "pos": [u["pos"]["x"], u["pos"]["y"]],
            "stats": {"base": {
                "HP": u.get("hp", 10),
                "AP": u.get("ap", 2),
                "ATK": u.get("strength", 3),
                "DEF": u.get("defense", 1),
                "MOV": 4, "RNG": 1, "CRIT": 5
            }},
            "items": [items[iid] for iid in u.get("item_ids", []) if iid in items],
            "injuries": [], "auras": [], "skills": [],
            "alive": u.get("hp", 10) > 0, "ap_left": u.get("ap", 2),
        }

    order = state.get("turn_order") or list(units.keys())
    active_index = state.get("active_index", 0)
    current_uid = order[active_index] if order else None
    side_to_move = "PLAYER" if state.get("active_side") == "A" else "ENEMY"

    mission = {
        "id": "m.from_state",
        "name": "From Tests",
        "map": {"width": width, "height": height, "tiles": tiles},
        "units": units,
        "side_to_move": side_to_move,
        "turn": state.get("turn_number", 1),
        "goals": [], "pre_events": [], "post_events": [], "global_mods": [],
        "current_unit_id": current_uid,
        "unit_order": order,
        "current_unit_index": active_index,
    }
    return mission

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

# ---------- info/templates ----------
def _defaults_info(base_url: str) -> dict:
    return _get(f"{base_url}/info")

def _unit_example(info: dict) -> dict:
    return copy.deepcopy(info["models"]["unit"]["example"])

def _item_example(info: dict) -> dict:
    return copy.deepcopy(info["models"]["item"]["example"])

def _attack_example(info: dict) -> dict:
    return copy.deepcopy(info["actions"]["attack"]["example"])  # {"kind":"ATTACK","attacker_id":"","target_id":""}

# ---------- tiny state builders (only tweak what’s under test) ----------
def _fresh_state_3x3() -> dict:
    # minimal shell; let model defaults fill the rest server-side
    return {
        "map": {"width": 3, "height": 3, "obstacles": []},
        "items": {},
        "units": {},
        "turn_order": [],
        "active_index": 0,
        "turn_number": 1,
        "status": "ongoing",
        "winner": None,
        "turn_mode": "unit",
        "active_side": "A",
    }

def _add_unit(st: dict, info: dict, *, uid: str, side: str, x: int, y: int, **overrides) -> None:
    u = _unit_example(info)
    u["id"] = uid
    u["side"] = side
    u["pos"] = {"x": x, "y": y}
    for k, v in overrides.items():
        u[k] = v
    st["units"][uid] = u
    st["turn_order"].append(uid)

def _add_item(st: dict, info: dict, *, iid: str, **overrides) -> None:
    it = _item_example(info)
    it["id"] = iid
    for k, v in overrides.items():
        it[k] = v
    st["items"][iid] = it

# ---------- verify/create helpers ----------
def _units_by_id(sess_json: dict) -> dict:
    units = sess_json.get("mission", {}).get("units", {})
    return units

def _hp_of(sess_json: dict, uid: str) -> int:
    u = _units_by_id(sess_json)[uid]
    return u["stats"]["base"]["HP"]

def _create_tbs_session_with_state(base_url: str, state: dict) -> tuple[str, dict]:
    """Create a TBS session using new typed Mission built from compact test state."""
    desired_ids = set((state.get("units") or {}).keys())
    mission = _mission_from_state(_defaults_info(base_url), state)
    body = {"mission": mission}

    sess = _post(f"{base_url}/sessions", body)
    sid = sess["id"]

    # fetch authoritative state after create
    sess = _get(f"{base_url}/sessions/{sid}")
    present_ids = set(_units_by_id(sess).keys())

    # sanity check: ensure server actually used our state
    if desired_ids and not desired_ids.issubset(present_ids):
        raise AssertionError(
            "Server did not accept the custom TBS State.\n"
            f"Wanted unit IDs: {sorted(desired_ids)}\n"
            f"Got unit IDs:    {sorted(present_ids)}\n"
            "The backend may be using quickstart() instead of the provided state."
        )

    return sid, sess

def _evaluate(base_url: str, sid: str, payload: dict) -> dict:
    return _post(f"{base_url}/sessions/{sid}/evaluate", {"action": payload})

def _apply(base_url: str, sid: str, payload: dict) -> dict:
    _post(f"{base_url}/sessions/{sid}/action", {"action": payload})
    # Always re-fetch so we assert against the stored state, not a handler echo
    return _session_get(base_url, sid)

# ---------- concrete scenarios ----------
def _make_state_for_adjacent_melee(info: dict) -> dict:
    st = _fresh_state_3x3()
    _add_unit(st, info, uid="A1", side="A", x=1, y=1, strength=5, defense=0, hp=10, max_hp=10, ap=2, max_ap=2)
    _add_unit(st, info, uid="B1", side="B", x=1, y=2, strength=3, defense=0, hp=10, max_hp=10, ap=2, max_ap=2)
    st["active_side"] = "A"
    st["active_index"] = 0
    return st

def _make_state_for_out_of_range(info: dict) -> dict:
    st = _fresh_state_3x3()
    _add_unit(st, info, uid="A2", side="A", x=0, y=0, strength=5, defense=0, hp=10, max_hp=10, ap=2, max_ap=2)
    _add_unit(st, info, uid="B2", side="B", x=2, y=2, strength=3, defense=0, hp=10, max_hp=10, ap=2, max_ap=2)
    st["active_side"] = "A"
    st["active_index"] = 0
    return st

def _make_state_for_ranged_gap(info: dict) -> dict:
    st = _fresh_state_3x3()
    # bow (+1 range) → effective range 2
    _add_item(st, info, iid="bow1", name="Bow", range_bonus=1, attack_bonus=0, defense_bonus=0)
    _add_unit(st, info, uid="A3", side="A", x=0, y=0, strength=4, defense=0, hp=10, max_hp=10, ap=2, max_ap=2)
    _add_unit(st, info, uid="B3", side="B", x=0, y=2, strength=3, defense=0, hp=10, max_hp=10, ap=2, max_ap=2)
    st["units"]["B3"]["item_ids"] = ["bow1"]
    st["active_side"] = "A"
    st["active_index"] = 1  # B3 is current for ranged attack
    return st

# ---------- tests ----------
def test_melee_adjacent_attack_applies_damage(base_url: str):
    info = _defaults_info(base_url)
    state = _make_state_for_adjacent_melee(info)

    sid, sess = _create_tbs_session_with_state(base_url, state)

    atk = _attack_example(info)
    atk["attacker_id"] = "A1"
    atk["target_id"]   = "B1"

    hp_before = _hp_of(sess, "B1")
    ex = _evaluate(base_url, sid, atk)
    assert ex.get("legal"), f"expected legal attack in evaluate, got {ex}"

    sess = _apply(base_url, sid, atk)
    hp_after = _hp_of(sess, "B1")

    assert hp_before - hp_after == 5, f"expected 5 damage, got {hp_before - hp_after}"
    assert hp_after == 5, f"expected B1 HP=5, got {hp_after}"

def test_melee_out_of_range_attack_rejected(base_url: str):
    info = _defaults_info(base_url)
    state = _make_state_for_out_of_range(info)

    sid, sess = _create_tbs_session_with_state(base_url, state)

    atk = _attack_example(info)
    atk["attacker_id"] = "A2"
    atk["target_id"]   = "B2"

    ex = _evaluate(base_url, sid, atk)
    assert not ex.get("legal", False), f"expected out-of-range to be illegal, got {ex}"

    with pytest.raises(requests.HTTPError):
        _apply(base_url, sid, atk)

def test_ranged_can_shoot_over_gap_melee_cannot(base_url: str):
    info = _defaults_info(base_url)
    state = _make_state_for_ranged_gap(info)

    sid, sess = _create_tbs_session_with_state(base_url, state)

    # melee should fail
    atk_fail = _attack_example(info)
    atk_fail["attacker_id"] = "A3"
    atk_fail["target_id"]   = "B3"
    ex = _evaluate(base_url, sid, atk_fail)
    assert not ex.get("legal", False), f"melee should be out of range, got {ex}"
    with pytest.raises(requests.HTTPError):
        _apply(base_url, sid, atk_fail)

    # ranged should succeed
    atk_ok = _attack_example(info)
    atk_ok["attacker_id"] = "B3"
    atk_ok["target_id"]   = "A3"
    ex2 = _evaluate(base_url, sid, atk_ok)
    assert ex2.get("legal"), f"expected legal ranged attack, got {ex2}"

    sess = _apply(base_url, sid, atk_ok)
    assert _hp_of(sess, "A3") == 7, f"expected A3 HP=7 after 3 damage"
