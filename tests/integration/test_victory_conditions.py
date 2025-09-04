# tests/integration/test_victory_conditions.py
import json

from backend.models.api import AttackAction
from backend.models.enums import StatName
from backend.models.mission import GoalKind, MissionGoal
from tests.integration.utils.data import (
    goblin_template,
    hero_template,
    simple_mission,
)
from tests.integration.utils.helpers import (
    _apply,
    _create_tbs_session,
    _evaluate,
    _hp_of,
)


def test_victory_on_eliminating_all_enemies(base_url: str):
    # 1. Setup units
    attacker = hero_template()
    target = goblin_template()

    # 2. Customize units for one-shot kill
    attacker.pos = (1, 1)
    attacker.stats.base[StatName.ATK] = 10

    target.pos = (1, 2)
    target.stats.base[StatName.HP] = 5
    target.stats.base[StatName.DEF] = 0

    # 3. Create mission with ELIMINATE_ALL_ENEMIES goal
    mission = simple_mission([attacker, target])
    mission.current_unit_id = attacker.id
    mission.goals = [MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)]

    # 4. Create session
    sid, sess = _create_tbs_session(base_url, mission)

    # 5. Attack and kill the target
    atk_action = AttackAction(attacker_id=attacker.id, target_id=target.id)
    atk_payload = json.loads(atk_action.model_dump_json())

    ex = _evaluate(base_url, sid, atk_payload)
    assert ex.get("legal"), f"expected legal attack, got {ex}"

    sess = _apply(base_url, sid, atk_payload)

    # 6. Check for victory
    assert _hp_of(sess, target.id) <= 0
    assert sess["mission"]["status"] == "VICTORY"


def test_victory_on_surviving_turns(base_url: str):
    # 1. Setup units
    unit_player = hero_template()
    unit_enemy = goblin_template()

    # 2. Create mission with SURVIVE_TURNS goal
    mission = simple_mission([unit_player, unit_enemy])
    mission.goals = [MissionGoal(kind=GoalKind.SURVIVE_TURNS, survive_turns=2)]
    mission.current_unit_id = unit_player.id

    # 3. Create session
    sid, sess = _create_tbs_session(base_url, mission)
    assert sess["mission"]["status"] == "IN_PROGRESS"

    # 4. End turn until victory
    end_turn_action = {"kind": "END_TURN"}

    # P1 T1
    sess = _apply(base_url, sid, end_turn_action)
    assert sess["mission"]["turn"] == 1
    assert sess["mission"]["status"] == "IN_PROGRESS"

    # E1 T1
    sess = _apply(base_url, sid, end_turn_action)
    assert sess["mission"]["turn"] == 2
    assert sess["mission"]["status"] == "VICTORY"

    # P1 T2
    sess = _apply(base_url, sid, end_turn_action)
    assert sess["mission"]["turn"] == 2
    assert sess["mission"]["status"] == "VICTORY"


def test_defeat_on_player_elimination(base_url: str):
    # 1. Setup units
    attacker = goblin_template()
    target = hero_template()

    # 2. Customize units for one-shot kill
    attacker.pos = (1, 1)
    attacker.stats.base[StatName.ATK] = 100  # Overkill
    attacker.stats.base[StatName.INIT] = 20  # Ensure enemy goes first

    target.pos = (1, 2)
    target.stats.base[StatName.HP] = 5

    # 3. Create mission
    mission = simple_mission([attacker, target])
    mission.goals = [MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)]

    # 4. Create session
    sid, sess = _create_tbs_session(base_url, mission)
    assert sess["mission"]["current_unit_id"] == attacker.id

    # 5. Attack and kill the player unit
    atk_action = AttackAction(attacker_id=attacker.id, target_id=target.id)
    atk_payload = json.loads(atk_action.model_dump_json())

    ex = _evaluate(base_url, sid, atk_payload)
    assert ex.get("legal"), f"expected legal attack, got {ex}"

    sess = _apply(base_url, sid, atk_payload)

    # 6. Check for defeat
    assert _hp_of(sess, target.id) <= 0
    assert sess["mission"]["status"] == "DEFEAT"
