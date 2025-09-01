from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field
from .common import (
    Aura, GoalKind, MapGrid, Mission, MissionEvent, MissionGoal,
    ModifierSource, Operation, Side, Skill, SkillKind, SkillTarget, StatBlock,
    StatModifier, StatName, Terrain, Tile, Unit, Item
)

class TBSSession(BaseModel):
    id: str
    mission: Mission

def default_demo_mission() -> Mission:
    width, height = 8, 8
    # Map terrain: a horizontal river at y==3 with a 2-tile bridge at x==3..4
    tiles = [
        [
            (
                Terrain.WATER
                if (y == 3 and x not in (3, 4))  # river except the bridge tiles
                else Terrain.PLAIN
            )
            for x in range(width)
        ]
        for y in range(height)
    ]
    grid = MapGrid(
        width=width,
        height=height,
        tiles=[[ 
            # no tile mods in demo
            Tile(terrain=t, mods=[]) for t in row
        ] for row in tiles]
    )

    iron_sword = Item(
        id="item.sword", name="Iron Sword",
        mods=[StatModifier(stat=StatName.ATK, operation=Operation.ADDITIVE, value=2, source=ModifierSource.ITEM)]
    )
    leather_armor = Item(
        id="item.armor", name="Leather Armor",
        mods=[StatModifier(stat=StatName.DEF, operation=Operation.ADDITIVE, value=1, source=ModifierSource.ITEM)]
    )

    passive_focus = Skill(
        id="skill.passive.focus", name="Keen Focus", kind=SkillKind.PASSIVE,
        passive_mods=[StatModifier(stat=StatName.CRIT, operation=Operation.ADDITIVE, value=10, source=ModifierSource.SKILL)]
    )
    active_shout = Skill(
        id="skill.active.shout", name="War Shout", kind=SkillKind.ACTIVE, ap_cost=1, range=2,
        target=SkillTarget.ALLY_UNIT,
        apply_mods=[StatModifier(stat=StatName.ATK, operation=Operation.ADDITIVE, value=1,
                                 source=ModifierSource.SKILL, duration_turns=2)],
        cooldown=2
    )

    u1 = Unit(
        id="u.player.1", side=Side.PLAYER, name="Hero", pos=(1, 1),
        stats=StatBlock(base={
            StatName.HP: 10, StatName.AP: 2, StatName.ATK: 3, StatName.DEF: 2,
            StatName.MOV: 4, StatName.RNG: 1, StatName.CRIT: 5
        }),
        items=[iron_sword, leather_armor],
        injuries=[],
        auras=[],  # add auras here if you like
        skills=[passive_focus, active_shout],
        ap_left=2
    )

    u2 = Unit(
        id="u.enemy.1", side=Side.ENEMY, name="Goblin", pos=(6, 6),
        stats=StatBlock(base={
            StatName.HP: 8, StatName.AP: 2, StatName.ATK: 2, StatName.DEF: 1,
            StatName.MOV: 3, StatName.RNG: 1, StatName.CRIT: 0
        }),
        items=[],
        injuries=[],
        auras=[],
        skills=[],
        ap_left=2
    )

    mission = Mission(
        id="m.demo",
        name="Bridge Clash",
        map=grid,
        units={u1.id: u1, u2.id: u2},
        side_to_move=Side.PLAYER,
        goals=[MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)],
        pre_events=[MissionEvent(id="e.start", text="Stop the goblin!")]
    )

    mission.unit_order = [u1.id, u2.id]
    mission.current_unit_id = u1.id
    mission.current_unit_index = 0

    return mission
