from __future__ import annotations
from typing import List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field
from .common import (
    GoalKind,
    MapGrid,
    Mission,
    MissionEvent,
    MissionGoal,
    ModifierSource,
    Operation,
    Side,
    Skill,
    SkillKind,
    SkillTarget,
    StatBlock,
    StatModifier,
    StatName,
    Terrain,
    Tile,
    Unit,
    Item,
)


class TBSSession(BaseModel):
    id: str
    mission: Mission


# ---------------- Explainable evaluation models ----------------


class TermKind(str, Enum):
    BASE = "base"
    ITEM = "item"
    ARTIFACT = "artifact"
    BUFF = "buff"
    DEBUFF = "debuff"
    STANCE = "stance"
    TERRAIN = "terrain"
    CONTEXT = "context"
    SKILL = "skill"
    OTHER = "other"


class Op(str, Enum):
    FLAT = "flat"  # +N
    MULT = "mult"  # +X% applied before final
    FINAL_MULT = "final_mult"  # +Y% applied at the very end


class StatTerm(BaseModel):
    kind: TermKind
    source: str
    op: Op
    value: float
    note: Optional[str] = None


class StatBreakdown(BaseModel):
    name: str
    base: float
    terms: List[StatTerm] = Field(default_factory=list)
    result: float


class ResistEntry(BaseModel):
    damage_type: Literal["physical", "magic", "true"]
    mult: float
    source: str


class Penetration(BaseModel):
    flat: float = 0.0
    pct: float = 0.0


class DamageBreakdown(BaseModel):
    damage_type: Literal["physical", "magic", "true"] = "physical"
    attack: StatBreakdown
    defense: StatBreakdown
    penetration: Penetration
    pre_mitigation: float
    effective_defense: float
    raw_after_def: float
    skill_ratio: float
    flat_power: float
    vulnerability_mults: List[ResistEntry] = Field(default_factory=list)
    attacker_damage_mults: List[StatTerm] = Field(default_factory=list)
    final_before_crit: float
    crit_chance: float
    crit_mult: float
    crit_expected: float
    block_flat: float
    block_mult: float
    final_after_block: float
    min_cap: Optional[float] = 1.0
    max_cap: Optional[float] = None
    final_capped: float
    immune: bool = False


class HitChanceBreakdown(BaseModel):
    accuracy: StatBreakdown
    evasion: StatBreakdown
    base: float
    mods: List[StatTerm] = Field(default_factory=list)
    result: float


class ActionEvaluation(BaseModel):
    action_type: Literal["attack", "skill", "item", "wait"] = "attack"
    attacker_id: str
    target_id: Optional[str] = None
    ap_cost: int
    summary: str
    expected_damage: float
    min_damage: float
    max_damage: float
    damage: Optional[DamageBreakdown] = None
    hit: Optional[HitChanceBreakdown] = None
    legality_ok: bool = True
    illegal_reasons: List[str] = Field(default_factory=list)


def default_demo_mission() -> Mission:
    width, height = 8, 8
    # Start with plains
    terrain = [[Terrain.PLAIN for _ in range(width)] for _ in range(height)]
    # Horizontal river at y == 3 with a 2-tile bridge at x == 3..4
    for x in range(width):
        if x not in (3, 4):
            terrain[3][x] = Terrain.WATER
    # Add some forests (defensive cover) and hills (high ground)
    forests = {(1, 0), (2, 0), (1, 1), (6, 2), (0, 5), (1, 5)}
    hills = {(6, 1), (2, 5), (5, 6)}
    blocked = {(0, 7)}  # a small rock outcrop that's impassable
    for x, y in forests:
        terrain[y][x] = Terrain.FOREST
    for x, y in hills:
        terrain[y][x] = Terrain.HILL
    for x, y in blocked:
        terrain[y][x] = Terrain.BLOCKED

    grid = MapGrid(
        width=width,
        height=height,
        tiles=[
            [Tile(terrain=terrain[y][x], mods=[]) for x in range(width)]
            for y in range(height)
        ],
    )

    iron_sword = Item(
        id="item.sword",
        name="Iron Sword",
        mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=2,
                source=ModifierSource.ITEM,
            )
        ],
    )
    leather_armor = Item(
        id="item.armor",
        name="Leather Armor",
        mods=[
            StatModifier(
                stat=StatName.DEF,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.ITEM,
            )
        ],
    )

    passive_focus = Skill(
        id="skill.passive.focus",
        name="Keen Focus",
        kind=SkillKind.PASSIVE,
        passive_mods=[
            StatModifier(
                stat=StatName.CRIT,
                operation=Operation.ADDITIVE,
                value=10,
                source=ModifierSource.SKILL,
            )
        ],
    )
    active_shout = Skill(
        id="skill.active.shout",
        name="War Shout",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=2,
        target=SkillTarget.ALLY_UNIT,
        apply_mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.SKILL,
                duration_turns=2,
            )
        ],
        cooldown=2,
    )

    # Additional unique items to diversify units
    short_bow = Item(
        id="item.bow.short",
        name="Short Bow",
        mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.ITEM,
            ),
            StatModifier(
                stat=StatName.RNG,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.ITEM,
            ),
        ],
    )
    light_boots = Item(
        id="item.boots.light",
        name="Light Boots",
        mods=[
            StatModifier(
                stat=StatName.MOV,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.ITEM,
            )
        ],
    )
    spiked_club = Item(
        id="item.club.spiked",
        name="Spiked Club",
        mods=[
            StatModifier(
                stat=StatName.ATK,
                operation=Operation.ADDITIVE,
                value=2,
                source=ModifierSource.ITEM,
            )
        ],
    )
    hide_shield = Item(
        id="item.shield.hide",
        name="Hide Shield",
        mods=[
            StatModifier(
                stat=StatName.DEF,
                operation=Operation.ADDITIVE,
                value=1,
                source=ModifierSource.ITEM,
            )
        ],
    )

    u1 = Unit(
        id="u.player.1",
        side=Side.PLAYER,
        name="Hero",
        pos=(1, 1),
        stats=StatBlock(
            base={
                StatName.HP: 10,
                StatName.AP: 2,
                StatName.ATK: 3,
                StatName.DEF: 2,
                StatName.MOV: 4,
                StatName.RNG: 1,
                StatName.CRIT: 5,
                StatName.INIT: 12,
            }
        ),
        items=[iron_sword, leather_armor],
        injuries=[],
        auras=[],  # add auras here if you like
        skills=[passive_focus, active_shout],
        ap_left=2,
    )

    u2 = Unit(
        id="u.enemy.1",
        side=Side.ENEMY,
        name="Goblin",
        pos=(6, 6),
        stats=StatBlock(
            base={
                StatName.HP: 8,
                StatName.AP: 2,
                StatName.ATK: 2,
                StatName.DEF: 1,
                StatName.MOV: 3,
                StatName.RNG: 1,
                StatName.CRIT: 0,
                StatName.INIT: 9,
            }
        ),
        items=[spiked_club],
        injuries=[],
        auras=[],
        skills=[],
        ap_left=2,
    )

    # Extra units: one per side with unique items
    u1b = Unit(
        id="u.player.2",
        side=Side.PLAYER,
        name="Archer",
        pos=(1, 2),
        stats=StatBlock(
            base={
                StatName.HP: 9,
                StatName.AP: 2,
                StatName.ATK: 2,
                StatName.DEF: 1,
                StatName.MOV: 4,
                StatName.RNG: 2,
                StatName.CRIT: 5,
                StatName.INIT: 14,
            }
        ),
        items=[short_bow, light_boots],
        injuries=[],
        auras=[],
        skills=[],
        ap_left=2,
    )
    u2b = Unit(
        id="u.enemy.2",
        side=Side.ENEMY,
        name="Orc",
        pos=(6, 5),
        stats=StatBlock(
            base={
                StatName.HP: 11,
                StatName.AP: 2,
                StatName.ATK: 3,
                StatName.DEF: 2,
                StatName.MOV: 3,
                StatName.RNG: 1,
                StatName.CRIT: 0,
                StatName.INIT: 8,
            }
        ),
        items=[hide_shield],
        injuries=[],
        auras=[],
        skills=[],
        ap_left=2,
    )

    mission = Mission(
        id="m.demo",
        name="Bridge Clash",
        map=grid,
        units={u1.id: u1, u1b.id: u1b, u2.id: u2, u2b.id: u2b},
        side_to_move=Side.PLAYER,
        goals=[MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)],
        pre_events=[MissionEvent(id="e.start", text="Stop the goblin!")],
    )

    return mission
