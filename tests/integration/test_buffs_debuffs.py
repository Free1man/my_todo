import json

from backend.models.api import AttackAction, UseSkillAction
from backend.models.enums import StatName
from tests.integration.utils.data import (
    goblin_template,
    heal_skill_template,
    hero_template,
    simple_mission,
    weaken_attack_skill_template,
)
from tests.integration.utils.helpers import (
    _apply,
    _create_tbs_session,
    _evaluate,
    _hp_of,
)


def test_heal_after_enemy_attack(base_url: str):
    # Setup: enemy near player; enemy acts first and hits, player heals on next turn
    player = hero_template()
    player.id = "player"
    player.pos = (1, 1)
    player.items = []
    # Give a heal skill
    player.skills = [heal_skill_template(amount=3)]

    enemy = goblin_template()
    enemy.id = "enemy"
    enemy.pos = (1, 2)
    enemy.stats.base[StatName.INIT] = 100  # enemy goes first to damage the player

    mission = simple_mission([player, enemy])

    sid, sess = _create_tbs_session(base_url, mission)

    # Enemy's turn: attack player
    assert sess["mission"]["current_unit_id"] == "enemy"
    hp0 = _hp_of(sess, "player")
    atk = AttackAction(attacker_id="enemy", target_id="player")
    atk_payload = json.loads(atk.model_dump_json())
    ex = _evaluate(base_url, sid, atk_payload)
    assert ex.get("legal"), ex
    sess = _apply(base_url, sid, atk_payload)
    hp_after_hit = _hp_of(sess, "player")
    assert hp_after_hit < hp0

    # Player's turn: heal self
    # End enemy turn so the player can act
    sess = _apply(base_url, sid, {"kind": "END_TURN"})
    assert sess["mission"]["current_unit_id"] == "player"
    heal = UseSkillAction(
        unit_id="player", skill_id="skill.heal.simple", target_unit_id="player"
    )
    heal_payload = json.loads(heal.model_dump_json())
    ex = _evaluate(base_url, sid, heal_payload)
    # evaluate() via legal_actions ignores skills without explain; ensure it's offered
    assert ex.get("legal"), ex
    sess = _apply(base_url, sid, heal_payload)
    hp_after_heal = _hp_of(sess, "player")
    assert hp_after_heal == min(hp0, hp_after_hit + 3)


def test_weaken_enemy_attack_reduces_damage(base_url: str):
    # Setup units adjacent; player weakens enemy before enemy attacks
    player = hero_template()
    player.id = "player"
    player.pos = (1, 1)
    player.items = []
    player.stats.base[StatName.INIT] = 100  # player goes first
    # Lower player's defense to make baseline damage > 1
    player.stats.base[StatName.DEF] = 0
    player.skills = [weaken_attack_skill_template(delta_atk=-2, duration_turns=2)]

    enemy = goblin_template()
    enemy.id = "enemy"
    enemy.pos = (1, 2)
    # Increase enemy attack so baseline damage is higher
    enemy.stats.base[StatName.ATK] = 4

    mission = simple_mission([player, enemy])
    mission.current_unit_id = "player"

    sid, sess = _create_tbs_session(base_url, mission)

    assert sess["mission"]["current_unit_id"] == "player"

    # Player casts weaken on enemy
    weaken = UseSkillAction(
        unit_id="player", skill_id="skill.debuff.weaken", target_unit_id="enemy"
    )
    weaken_payload = json.loads(weaken.model_dump_json())
    ex = _evaluate(base_url, sid, weaken_payload)
    assert ex.get("legal"), ex
    sess = _apply(base_url, sid, weaken_payload)

    # End player's turn so enemy can act
    sess = _apply(base_url, sid, {"kind": "END_TURN"})
    assert sess["mission"]["current_unit_id"] == "enemy"

    # Record player's HP before enemy attack
    hp_before = _hp_of(sess, "player")

    # Enemy attacks
    atk = AttackAction(attacker_id="enemy", target_id="player")
    atk_payload = json.loads(atk.model_dump_json())
    ex = _evaluate(base_url, sid, atk_payload)
    assert ex.get("legal"), ex
    sess = _apply(base_url, sid, atk_payload)
    hp_after = _hp_of(sess, "player")

    dmg_with_debuff = hp_before - hp_after

    # Now compute a baseline by recreating scenario without debuff
    player2 = hero_template()
    player2.id = "p2"
    player2.pos = (1, 1)
    player2.items = []
    # Mirror defense change from the main scenario
    player2.stats.base[StatName.DEF] = 0

    enemy2 = goblin_template()
    enemy2.id = "e2"
    enemy2.pos = (1, 2)
    # Mirror attack change from the main scenario
    enemy2.stats.base[StatName.ATK] = 4

    mission2 = simple_mission([player2, enemy2])
    mission2.current_unit_id = "e2"  # make enemy attack immediately
    sid2, sess2 = _create_tbs_session(base_url, mission2)
    hp2_before = _hp_of(sess2, "p2")
    atk2 = AttackAction(attacker_id="e2", target_id="p2")
    atk2_payload = json.loads(atk2.model_dump_json())
    ex2 = _evaluate(base_url, sid2, atk2_payload)
    assert ex2.get("legal"), ex2
    sess2 = _apply(base_url, sid2, atk2_payload)
    hp2_after = _hp_of(sess2, "p2")
    dmg_without_debuff = hp2_before - hp2_after

    # Ensure debuff reduced damage
    assert (
        dmg_with_debuff < dmg_without_debuff
    ), f"expected debuff to reduce damage, got with={dmg_with_debuff}, without={dmg_without_debuff}"

    # Advance two turns to let debuff expire on enemy, then enemy attacks again
    # 1) End enemy's current turn -> player's turn
    sess = _apply(base_url, sid, {"kind": "END_TURN"})
    assert sess["mission"]["current_unit_id"] == "player"
    # 2) End player's turn -> back to enemy
    sess = _apply(base_url, sid, {"kind": "END_TURN"})
    assert sess["mission"]["current_unit_id"] == "enemy"

    # Attack again; debuff should be gone now
    hp_before2 = _hp_of(sess, "player")
    atk3 = AttackAction(attacker_id="enemy", target_id="player")
    atk3_payload = json.loads(atk3.model_dump_json())
    ex3 = _evaluate(base_url, sid, atk3_payload)
    assert ex3.get("legal"), ex3
    sess = _apply(base_url, sid, atk3_payload)
    hp_after2 = _hp_of(sess, "player")
    dmg_after_expire = hp_before2 - hp_after2

    # Debuff expired: damage should be back to baseline and also higher than with-debuff
    assert dmg_after_expire == dmg_without_debuff
    assert dmg_after_expire > dmg_with_debuff
