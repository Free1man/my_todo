# tests/integration/test_api_tbs.py
import json
import pytest
import requests
from backend.models.api import AttackAction
from backend.models.common import Mission, Unit, StatName, MapGrid, Tile, Terrain, Side, GoalKind, MissionGoal
from tests.integration.templates import hero_template, goblin_template, archer_template, iron_sword_template, short_bow_template

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

def _simple_mission(units: list[Unit], width: int = 3, height: int = 3) -> Mission:
    grid = MapGrid(
        width=width,
        height=height,
        tiles=[[Tile(terrain=Terrain.PLAIN) for _ in range(width)] for _ in range(height)]
    )
    unit_map = {u.id: u for u in units}
    return Mission(
        id="m.test", name="Test Mission", map=grid, units=unit_map,
        side_to_move=Side.PLAYER,
        goals=[MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)]
    )

# ---------- tests ----------
def test_melee_adjacent_attack_applies_damage(base_url: str):
    # 1. Setup units from templates
    attacker = hero_template()
    target = goblin_template()

    # 2. Customize units for the test
    attacker.pos = (1, 1)
    attacker.stats.base[StatName.ATK] = 5 # Override base attack
    attacker.items = [] # No items for this test

    target.pos = (1, 2)
    target.stats.base[StatName.HP] = 10
    target.stats.base[StatName.DEF] = 0

    # 3. Create mission
    mission = _simple_mission([attacker, target])
    mission.current_unit_id = attacker.id

    # 4. Create session and run simulation
    sid, sess = _create_tbs_session(base_url, mission)

    atk_action = AttackAction(attacker_id=attacker.id, target_id=target.id)
    atk_payload = json.loads(atk_action.model_dump_json())

    hp_before = _hp_of(sess, target.id)
    ex = _evaluate(base_url, sid, atk_payload)
    assert ex.get("legal"), f"expected legal attack, got {ex}"

    sess = _apply(base_url, sid, atk_payload)
    hp_after = _hp_of(sess, target.id)

    # 5. Confirm damage
    expected_damage = 5
    assert hp_before - hp_after == expected_damage, f"Expected {expected_damage} damage, but got {hp_before - hp_after}"

def test_melee_out_of_range_attack_rejected(base_url: str):
    # 1. Setup units
    attacker = hero_template()
    target = goblin_template()

    # 2. Customize
    attacker.pos = (0, 0)
    target.pos = (2, 2) # Out of default range 1

    # 3. Create mission
    mission = _simple_mission([attacker, target])
    mission.current_unit_id = attacker.id

    # 4. Create session and run
    sid, _ = _create_tbs_session(base_url, mission)

    atk_action = AttackAction(attacker_id=attacker.id, target_id=target.id)
    atk_payload = json.loads(atk_action.model_dump_json())

    ex = _evaluate(base_url, sid, atk_payload)
    assert not ex.get("legal", False), f"expected out-of-range to be illegal, got {ex}"

    with pytest.raises(requests.HTTPError):
        _apply(base_url, sid, atk_payload)

def test_ranged_can_shoot_over_gap_melee_cannot(base_url: str):
    # 1. Setup units
    melee_unit = hero_template()
    ranged_unit = archer_template()

    # 2. Customize and assign items
    melee_unit.pos = (0, 0)
    melee_unit.items = [] # No items
    melee_unit.stats.base[StatName.INIT] = 100

    ranged_unit.pos = (0, 2)
    ranged_unit.items = [short_bow_template()] 
    ranged_unit.stats.base[StatName.ATK] = 4

    # 3. Create mission
    mission = _simple_mission([melee_unit, ranged_unit])

    # 4. Create session
    sid, _ = _create_tbs_session(base_url, mission)

    # 5. Melee should fail
    atk_fail_action = AttackAction(attacker_id=melee_unit.id, target_id=ranged_unit.id)
    atk_fail_payload = json.loads(atk_fail_action.model_dump_json())
    ex = _evaluate(base_url, sid, atk_fail_payload)
    assert not ex.get("legal", False), f"melee should be out of range, got {ex}"

    # 6. End turn for melee unit to pass turn to the ranged unit
    end_turn_action = {"kind": "END_TURN"}
    sess = _apply(base_url, sid, end_turn_action)
    assert sess['mission']['current_unit_id'] == ranged_unit.id

    # 7. Ranged should succeed
    atk_ok_action = AttackAction(attacker_id=ranged_unit.id, target_id=melee_unit.id)
    atk_ok_payload = json.loads(atk_ok_action.model_dump_json())
    ex2 = _evaluate(base_url, sid, atk_ok_payload)
    assert ex2.get("legal"), f"expected legal ranged attack, got {ex2}"

    hp_before = _hp_of(sess, melee_unit.id)
    sess = _apply(base_url, sid, atk_ok_payload)
    hp_after = _hp_of(sess, melee_unit.id)

    assert hp_before - hp_after == 3, f"expected 3 damage, got {hp_before - hp_after}"

def test_initiative_and_turn_order(base_url: str):
    # 1. Setup units with different initiative scores
    unit_fast = hero_template()
    unit_fast.id = "unit_fast"
    unit_fast.stats.base[StatName.INIT] = 20

    unit_mid = goblin_template()
    unit_mid.id = "unit_mid"
    unit_mid.stats.base[StatName.INIT] = 15

    unit_slow = archer_template()
    unit_slow.id = "unit_slow"
    unit_slow.stats.base[StatName.INIT] = 10

    # 2. Create mission - order of units in list shouldn't matter
    mission = _simple_mission([unit_slow, unit_mid, unit_fast])

    # 3. Create session and check initial state
    # Engine should sort by INIT: fast, mid, slow
    sid, sess = _create_tbs_session(base_url, mission)
    assert sess['mission']['turn'] == 1
    assert sess['mission']['current_unit_id'] == "unit_fast"

    # 4. End turn 1 (fast -> mid)
    end_turn_action = {"kind": "END_TURN"}
    sess = _apply(base_url, sid, end_turn_action)
    assert sess['mission']['turn'] == 1
    assert sess['mission']['current_unit_id'] == "unit_mid"

    # 5. End turn 2 (mid -> slow)
    sess = _apply(base_url, sid, end_turn_action)
    assert sess['mission']['turn'] == 1
    assert sess['mission']['current_unit_id'] == "unit_slow"

    # 6. End turn 3 (slow -> fast, wraps around to a new turn)
    sess = _apply(base_url, sid, end_turn_action)
    assert sess['mission']['turn'] == 2
    assert sess['mission']['current_unit_id'] == "unit_fast"
