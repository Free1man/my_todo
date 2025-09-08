import json

import pytest
from backend.models.api import UseSkillAction
from backend.models.enums import StatName
from tests.integration.utils.data import (
    fireball_skill_template,
    goblin_template,
    hero_template,
    simple_mission,
)
from tests.integration.utils.helpers import _apply, _create_tbs_session, _hp_of


@pytest.mark.timeout(30)
def test_fireball_cross_shape_hits_all_in_cross(base_url: str):
    """Cross-shaped Fireball (plus shape) should hit center-adjacent tiles and not diagonals.
    Place one unit in the center (target tile is center), and four around it (up,down,left,right).
    Verify all four around get damaged; center gets damaged too; diagonals remain unharmed.
    """
    # Setup player caster with Fireball and enough AP
    caster = hero_template()
    caster.id = "caster"
    caster.pos = (2, 2)
    caster.items = []
    caster.skills = [fireball_skill_template(power=3, rng=5, ap_cost=1)]
    caster.stats.base[StatName.INIT] = 100

    # Enemies: 4 on cross arms, 1 on center, 4 on diagonals for sanity
    foes = []
    positions_hit = [(2, 1), (2, 3), (1, 2), (3, 2), (2, 2)]  # U D L R center
    positions_miss = [(1, 1), (3, 1), (1, 3), (3, 3)]  # diagonals

    for i, p in enumerate(positions_hit):
        g = goblin_template()
        g.id = f"hit_{i}"
        g.pos = p
        foes.append(g)
    for i, p in enumerate(positions_miss):
        g = goblin_template()
        g.id = f"miss_{i}"
        g.pos = p
        foes.append(g)

    mission = simple_mission([caster, *foes], width=5, height=5)
    mission.current_unit_id = caster.id

    sid, sess = _create_tbs_session(base_url, mission)

    # Snapshot HP before
    hp_before = {u.id: _hp_of(sess, u.id) for u in mission.units.values()}

    # Cross shape offsets (plus shape centered on target tile)
    cross_offsets = [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]
    action = UseSkillAction(
        unit_id=caster.id,
        skill_id="skill.fireball",
        target_tile=(2, 2),
        area_offsets=cross_offsets,
    )
    payload = json.loads(action.model_dump_json())

    # Apply and verify
    sess = _apply(base_url, sid, payload)

    # Expect all in positions_hit to lose 3 HP, center included if an enemy is there
    for uid in [f"hit_{i}" for i in range(len(positions_hit))]:
        assert _hp_of(sess, uid) == hp_before[uid] - 3
    # Diagonals should be unaffected
    for uid in [f"miss_{i}" for i in range(len(positions_miss))]:
        assert _hp_of(sess, uid) == hp_before[uid]


@pytest.mark.timeout(30)
def test_fireball_default_3x3_hits_corners_when_aimed_center(base_url: str):
    """With default 3x3 shape (no area_offsets provided), a center-aimed Fireball should hit all 8 neighbors and center.
    Place four enemies in the corners of a 3x3 block centered at (2,2). Aim at (2,2) and verify all four corners are damaged.
    """
    caster = hero_template()
    caster.id = "caster"
    caster.pos = (2, 2)
    caster.items = []
    caster.skills = [fireball_skill_template(power=2, rng=5, ap_cost=1)]
    caster.stats.base[StatName.INIT] = 100

    corners = [(1, 1), (3, 1), (1, 3), (3, 3)]
    foes = []
    for i, p in enumerate(corners):
        g = goblin_template()
        g.id = f"corner_{i}"
        g.pos = p
        foes.append(g)

    mission = simple_mission([caster, *foes], width=5, height=5)
    mission.current_unit_id = caster.id

    sid, sess = _create_tbs_session(base_url, mission)

    hp_before = {u.id: _hp_of(sess, u.id) for u in mission.units.values()}

    action = UseSkillAction(
        unit_id=caster.id,
        skill_id="skill.fireball",
        target_tile=(2, 2),  # center of 3x3 block
        # no area_offsets -> engine defaults to 3x3
    )
    payload = json.loads(action.model_dump_json())

    sess = _apply(base_url, sid, payload)

    for uid in [f"corner_{i}" for i in range(4)]:
        assert _hp_of(sess, uid) == hp_before[uid] - 2


@pytest.mark.timeout(30)
def test_fireball_two_tile_shape_can_kill_enemy(base_url: str):
    """Custom AoE with only two tiles should apply damage only to those tiles.
    Use a very high fireball power to ensure one enemy inside the area dies (HP reaches 0).
    """
    caster = hero_template()
    caster.id = "caster"
    caster.pos = (2, 2)
    caster.items = []
    caster.skills = [fireball_skill_template(power=20, rng=5, ap_cost=1)]  # high dmg
    caster.stats.base[StatName.INIT] = 100

    # Two-tile shape: center and one tile to the right
    two_tile_offsets = [(0, 0), (1, 0)]

    # Enemy inside AoE (to be killed)
    kill_me = goblin_template()
    kill_me.id = "kill_me"
    kill_me.pos = (3, 2)  # (2,2) + (1,0)

    # Enemy outside AoE (should not be hit)
    miss = goblin_template()
    miss.id = "miss"
    miss.pos = (1, 1)

    mission = simple_mission([caster, kill_me, miss], width=5, height=5)
    mission.current_unit_id = caster.id

    sid, sess = _create_tbs_session(base_url, mission)

    hp_before = {u.id: _hp_of(sess, u.id) for u in mission.units.values()}

    action = UseSkillAction(
        unit_id=caster.id,
        skill_id="skill.fireball",
        target_tile=(2, 2),
        area_offsets=two_tile_offsets,
    )
    payload = json.loads(action.model_dump_json())

    sess = _apply(base_url, sid, payload)

    # kill_me should be reduced to 0 HP; miss unchanged; caster (ally) on center tile unaffected
    assert _hp_of(sess, "kill_me") == 0
    assert sess["mission"]["units"]["kill_me"]["alive"] is False
    assert _hp_of(sess, "miss") == hp_before["miss"]
