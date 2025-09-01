# tests/integration/test_api_tbs.py
import json
import copy
import pytest
import requests

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

# ---------- info/templates ----------
def _tbs_info(base_url: str) -> dict:
    """Ruleset-level info with action/model templates."""
    return _get(f"{base_url}/rulesets/tbs/info")

def _attack_tpl(info: dict) -> dict:
    """Canonical attack payload from info endpoint."""
    # expected: {"type":"attack","attacker_id":"...","target_id":"..."}
    return copy.deepcopy(info["actions"]["attack"]["template"])

def _unit_tpl(info: dict) -> dict:
    return copy.deepcopy(info["models"]["unit"]["template"])

def _item_tpl(info: dict) -> dict:
    return copy.deepcopy(info["models"]["item"]["template"])

# ---------- session creation using model templates ----------
def _make_state_for_adjacent_melee(info: dict):
    """Two adjacent melee units; A hits B for 5 dmg (10 -> 5)."""
    unit = _unit_tpl(info)

    A = copy.deepcopy(unit)
    A["id"] = "A1"; A["side"] = "A"; A["name"] = "MeleeA"
    A["strength"] = 5; A["defense"] = 0
    A["max_hp"] = 10; A["hp"] = 10
    A["max_ap"] = 2;  A["ap"] = 2
    A["pos"] = {"x": 1, "y": 1}
    A["item_ids"] = []

    B = copy.deepcopy(unit)
    B["id"] = "B1"; B["side"] = "B"; B["name"] = "TargetB"
    B["strength"] = 3; B["defense"] = 0
    B["max_hp"] = 10; B["hp"] = 10
    B["max_ap"] = 2;  B["ap"] = 2
    B["pos"] = {"x": 1, "y": 2}
    B["item_ids"] = []

    state = {
        "map": {"width": 3, "height": 3, "obstacles": []},
        "items": {},
        "units": {"A1": A, "B1": B},
        "turn_order": ["A1", "B1"],
        "active_index": 0,
        "turn_mode": "unit",
        "status": "ongoing",
        "active_side": "A",
    }
    return state

def _make_state_for_out_of_range(info: dict):
    """Two melee units far apart; attack must be illegal."""
    unit = _unit_tpl(info)

    A = copy.deepcopy(unit)
    A["id"] = "A2"; A["side"] = "A"; A["name"] = "MeleeA"
    A["strength"] = 5; A["defense"] = 0
    A["max_hp"] = 10; A["hp"] = 10
    A["max_ap"] = 2;  A["ap"] = 2
    A["pos"] = {"x": 0, "y": 0}
    A["item_ids"] = []                       # range = 1

    B = copy.deepcopy(unit)
    B["id"] = "B2"; B["side"] = "B"; B["name"] = "MeleeB"
    B["strength"] = 3; B["defense"] = 0
    B["max_hp"] = 10; B["hp"] = 10
    B["max_ap"] = 2;  B["ap"] = 2
    B["pos"] = {"x": 2, "y": 2}
    B["item_ids"] = []                       # range = 1

    state = {
        "map": {"width": 3, "height": 3, "obstacles": []},
        "items": {},
        "units": {"A2": A, "B2": B},
        "turn_order": ["A2", "B2"],
        "active_index": 0,
        "turn_mode": "unit",
        "status": "ongoing",
        "active_side": "A",
    }
    return state

def _make_state_for_ranged_gap(info: dict):
    """
    Column 0: (0,0)=A3 melee, (0,1)=empty, (0,2)=B3 archer (range 2 via range_bonus=1).
    """
    unit = _unit_tpl(info)
    item = _item_tpl(info)

    # Archer item: base range 1 + 1 bonus = 2
    bow = copy.deepcopy(item)
    bow["id"] = "bow1"
    bow["name"] = "Bow"
    bow["attack_bonus"] = 0
    bow["defense_bonus"] = 0
    bow["range_bonus"] = 1

    A = copy.deepcopy(unit)
    A["id"] = "A3"; A["side"] = "A"; A["name"] = "MeleeA"
    A["strength"] = 4; A["defense"] = 0
    A["max_hp"] = 10; A["hp"] = 10
    A["max_ap"] = 2;  A["ap"] = 2
    A["pos"] = {"x": 0, "y": 0}
    A["item_ids"] = []                       # melee only

    B = copy.deepcopy(unit)
    B["id"] = "B3"; B["side"] = "B"; B["name"] = "ArcherB"
    B["strength"] = 3; B["defense"] = 0
    B["max_hp"] = 10; B["hp"] = 10
    B["max_ap"] = 2;  B["ap"] = 2
    B["pos"] = {"x": 0, "y": 2}
    B["item_ids"] = ["bow1"]                 # gets +1 range

    state = {
        "map": {"width": 3, "height": 3, "obstacles": []},
        "items": {"bow1": bow},
        "units": {"A3": A, "B3": B},
        "turn_order": ["A3", "B3"],
        "active_index": 0,
        "turn_mode": "unit",
        "status": "ongoing",
        "active_side": "A",
    }
    return state

# ---------- tiny state readers ----------
def _units_by_id(sess_json: dict) -> dict[str, dict]:
    state = sess_json.get("state", {})
    units = state.get("units", {})
    if isinstance(units, list):
        return {u["id"]: u for u in units}
    return units

def _hp_of(sess_json: dict, uid: str) -> int:
    u = _units_by_id(sess_json)[uid]
    return u["hp"]["current"] if isinstance(u.get("hp"), dict) else u["hp"]

# ---------- simple evaluate/apply wrappers ----------
def _evaluate(base_url: str, sid: str, payload: dict) -> dict:
    return _post(f"{base_url}/sessions/{sid}/evaluate", payload)

def _apply(base_url: str, sid: str, payload: dict) -> dict:
    return _post(f"{base_url}/sessions/{sid}/action", payload)

# ---------- tests ----------

def test_melee_adjacent_attack_applies_damage(base_url: str):
    """
    Two units adjacent; melee A hits B; damage = strength - defense (min 1) = 5.
    """
    info = _tbs_info(base_url)
    state = _make_state_for_adjacent_melee(info)

    # Create session with full State (no spawn action in TBS)
    sess = _post(f"{base_url}/sessions", {"ruleset": "tbs", **state})
    sid = sess["id"]

    atk = _attack_tpl(info)
    atk["attacker_id"] = "A1"
    atk["target_id"]   = "B1"

    hp_before = _hp_of(sess, "B1")
    ex = _evaluate(base_url, sid, atk)
    assert ex.get("ok") in (True, None), f"expected legal attack in evaluate, got {ex}"

    sess = _apply(base_url, sid, atk)
    hp_after = _hp_of(sess, "B1")

    assert hp_before - hp_after == 5, f"expected 5 damage, got {hp_before - hp_after}"
    assert hp_after == 5, f"expected B1 HP=5, got {hp_after}"

def test_melee_out_of_range_attack_rejected(base_url: str):
    """
    A at (0,0) vs B at (2,2): manhattan 4 > range 1 → illegal.
    """
    info = _tbs_info(base_url)
    state = _make_state_for_out_of_range(info)

    sess = _post(f"{base_url}/sessions", {"ruleset": "tbs", **state})
    sid = sess["id"]

    atk = _attack_tpl(info)
    atk["attacker_id"] = "A2"
    atk["target_id"]   = "B2"

    ex = _evaluate(base_url, sid, atk)
    # Engine's evaluate should flag it illegal
    assert not ex.get("ok", False), f"expected out-of-range to be illegal, got {ex}"

    # And /action should reject (prefer 4xx; if your engine returns 200 with ok:false, adjust here)
    with pytest.raises(requests.HTTPError):
        _apply(base_url, sid, atk)

def test_ranged_can_shoot_over_gap_melee_cannot(base_url: str):
    """
    Column 0: (0,0)=A3 melee, (0,1)=empty, (0,2)=B3 archer (range 2 via +1 item).
    Melee cannot reach; archer can hit A3 for 3 damage.
    """
    info = _tbs_info(base_url)
    state = _make_state_for_ranged_gap(info)

    sess = _post(f"{base_url}/sessions", {"ruleset": "tbs", **state})
    sid = sess["id"]

    # melee should fail
    atk_fail = _attack_tpl(info)
    atk_fail["attacker_id"] = "A3"
    atk_fail["target_id"]   = "B3"
    ex = _evaluate(base_url, sid, atk_fail)
    assert not ex.get("ok", False), f"melee should be out of range, got {ex}"
    with pytest.raises(requests.HTTPError):
        _apply(base_url, sid, atk_fail)

    # ranged should succeed
    atk_ok = _attack_tpl(info)
    atk_ok["attacker_id"] = "B3"
    atk_ok["target_id"]   = "A3"
    ex2 = _evaluate(base_url, sid, atk_ok)
    assert ex2.get("ok") in (True, None), f"expected legal ranged attack, got {ex2}"

    sess = _apply(base_url, sid, atk_ok)
    assert _hp_of(sess, "A3") == 7, f"expected A3 HP=7 after 3 damage"
