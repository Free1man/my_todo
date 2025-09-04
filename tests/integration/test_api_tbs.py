# tests/integration/test_api_tbs.py
import json
import pytest
import requests
from backend.models.api import AttackAction
from backend.models.common import StatName
from tests.integration.utils.data import (
    archer_template,
    goblin_template,
    hero_template,
    short_bow_template,
    simple_mission,
)
from tests.integration.utils.helpers import (
    _apply,
    _create_tbs_session,
    _evaluate,
    _hp_of,
)
import requests as _requests


# ---------- tests ----------
def test_melee_adjacent_attack_applies_damage(base_url: str):
    # 1. Setup units from templates
    attacker = hero_template()
    target = goblin_template()

    # 2. Customize units for the test
    attacker.pos = (1, 1)
    attacker.stats.base[StatName.ATK] = 5  # Override base attack
    attacker.items = []  # No items for this test

    target.pos = (1, 2)
    target.stats.base[StatName.HP] = 10
    target.stats.base[StatName.DEF] = 0

    # 3. Create mission
    mission = simple_mission([attacker, target])
    mission.current_unit_id = attacker.id

    # 4. Create session and run simulation
    sid, sess = _create_tbs_session(base_url, mission)

    atk_action = AttackAction(attacker_id=attacker.id, target_id=target.id)
    atk_payload = json.loads(atk_action.model_dump_json())

    hp_before = _hp_of(sess, target.id)
    ex = _evaluate(base_url, sid, atk_payload)
    assert ex.get("legal"), f"expected legal attack, got {ex}"

    # Explainable evaluation via legal_actions?explain=true
    la = _requests.get(
        f"{base_url}/sessions/{sid}/legal_actions",
        params={"explain": "true"},
        timeout=5,
    )
    la.raise_for_status()
    acts = la.json()["actions"]
    # find our attack action entry
    evj = next(
        (
            a.get("evaluation")
            for a in acts
            if a.get("action", {}).get("kind") == "ATTACK"
            and a.get("action", {}).get("attacker_id") == attacker.id
            and a.get("action", {}).get("target_id") == target.id
        ),
        None,
    )
    assert evj is not None, f"expected evaluation for ATTACK {attacker.id}->{target.id}"
    assert evj["action_type"] == "attack"
    assert evj["attacker_id"] == attacker.id and evj["target_id"] == target.id
    assert isinstance(evj.get("expected_damage"), (int, float))
    assert "Hit" in evj.get("summary", "")

    sess = _apply(base_url, sid, atk_payload)
    hp_after = _hp_of(sess, target.id)

    # 5. Confirm damage
    expected_damage = 5
    actual = hp_before - hp_after
    assert (
        actual == expected_damage
    ), f"Expected {expected_damage} damage, but got {actual}"
    # Expected damage preview should be within the min..max range and close to actual (same in this simple model)
    assert evj["min_damage"] <= evj["expected_damage"] <= evj["max_damage"]
    assert int(evj["expected_damage"]) == actual


def test_melee_out_of_range_attack_rejected(base_url: str):
    # 1. Setup units
    attacker = hero_template()
    target = goblin_template()

    # 2. Customize
    attacker.pos = (0, 0)
    target.pos = (2, 2)  # Out of default range 1

    # 3. Create mission
    mission = simple_mission([attacker, target])
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
    melee_unit.items = []  # No items
    melee_unit.stats.base[StatName.INIT] = 100

    ranged_unit.pos = (0, 2)
    ranged_unit.items = [short_bow_template()]
    ranged_unit.stats.base[StatName.ATK] = 4

    # 3. Create mission
    mission = simple_mission([melee_unit, ranged_unit])

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
    assert sess["mission"]["current_unit_id"] == ranged_unit.id

    # 7. Ranged should succeed
    atk_ok_action = AttackAction(attacker_id=ranged_unit.id, target_id=melee_unit.id)
    atk_ok_payload = json.loads(atk_ok_action.model_dump_json())
    ex2 = _evaluate(base_url, sid, atk_ok_payload)
    assert ex2.get("legal"), f"expected legal ranged attack, got {ex2}"

    hp_before = _hp_of(sess, melee_unit.id)
    # Check explainable evaluation via legal_actions
    la = _requests.get(
        f"{base_url}/sessions/{sid}/legal_actions",
        params={"explain": "true"},
        timeout=5,
    )
    la.raise_for_status()
    acts = la.json()["actions"]
    evj = next(
        (
            a.get("evaluation")
            for a in acts
            if a.get("action", {}).get("kind") == "ATTACK"
            and a.get("action", {}).get("attacker_id") == ranged_unit.id
            and a.get("action", {}).get("target_id") == melee_unit.id
        ),
        None,
    )
    assert evj is not None
    assert evj["action_type"] == "attack"
    assert evj["attacker_id"] == ranged_unit.id and evj["target_id"] == melee_unit.id
    assert evj["min_damage"] <= evj["expected_damage"] <= evj["max_damage"]
    assert evj["hit"]["result"] == 100
    sess = _apply(base_url, sid, atk_ok_payload)
    hp_after = _hp_of(sess, melee_unit.id)

    actual = hp_before - hp_after
    assert actual == 3, f"expected 3 damage, got {actual}"
    assert int(evj["expected_damage"]) == actual


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
    mission = simple_mission([unit_slow, unit_mid, unit_fast])

    # 3. Create session and check initial state
    # Engine should sort by INIT: fast, mid, slow
    sid, sess = _create_tbs_session(base_url, mission)
    assert sess["mission"]["turn"] == 1
    assert sess["mission"]["current_unit_id"] == "unit_fast"

    # 4. End turn 1 (fast -> mid)
    end_turn_action = {"kind": "END_TURN"}
    sess = _apply(base_url, sid, end_turn_action)
    assert sess["mission"]["turn"] == 1
    assert sess["mission"]["current_unit_id"] == "unit_mid"

    # 5. End turn 2 (mid -> slow)
    sess = _apply(base_url, sid, end_turn_action)
    assert sess["mission"]["turn"] == 1
    assert sess["mission"]["current_unit_id"] == "unit_slow"

    # 6. End turn 3 (slow -> fast, wraps around to a new turn)
    sess = _apply(base_url, sid, end_turn_action)
    assert sess["mission"]["turn"] == 2
    assert sess["mission"]["current_unit_id"] == "unit_fast"
