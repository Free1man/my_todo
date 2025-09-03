# tests/integration/utils/data.py
from __future__ import annotations
from backend.models.common import (
    GoalKind,
    Item,
    Skill,
    SkillKind,
    SkillTarget,
    MapGrid,
    Mission,
    MissionGoal,
    Operation,
    Side,
    StatBlock,
    StatModifier,
    StatName,
    Terrain,
    Tile,
    Unit,
    ModifierSource,
)

# ----- Item Templates -----

def iron_sword_template() -> Item:
    """A basic melee weapon."""
    return Item(
        id="item.sword.iron", name="Iron Sword",
        mods=[StatModifier(stat=StatName.ATK, operation=Operation.ADDITIVE, value=2, source=ModifierSource.ITEM)]
    )

def short_bow_template() -> Item:
    """A basic ranged weapon that increases range."""
    return Item(
        id="item.bow.short", name="Short Bow",
        mods=[
            StatModifier(stat=StatName.ATK, operation=Operation.ADDITIVE, value=1, source=ModifierSource.ITEM),
            StatModifier(stat=StatName.RNG, operation=Operation.ADDITIVE, value=1, source=ModifierSource.ITEM),
        ]
    )

# ----- Skill Templates -----

def heal_skill_template(amount: int = 3, *, duration_turns: int | None = None) -> Skill:
    """Simple heal skill that restores HP to an ally or self.
    If duration_turns is provided with multiplicative/other ops it would be temporary; we use flat additive HP.
    Costs 1 AP, range 3, target ally (including self when passed explicitly by tests using target_unit_id).
    """
    return Skill(
        id="skill.heal.simple",
        name="Heal",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=3,
        target=SkillTarget.ALLY_UNIT,
        cooldown=0,
        apply_mods=[
            StatModifier(stat=StatName.HP, operation=Operation.ADDITIVE, value=amount, source=ModifierSource.SKILL, duration_turns=duration_turns)
        ],
    )

def weaken_attack_skill_template(delta_atk: int = -2, *, duration_turns: int = 2) -> Skill:
    """Debuff that reduces enemy ATK for a few turns (default 2). Costs 1 AP, range 3, target enemy."""
    return Skill(
        id="skill.debuff.weaken",
        name="Weaken",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=3,
        target=SkillTarget.ENEMY_UNIT,
        cooldown=0,
        apply_mods=[
            StatModifier(stat=StatName.ATK, operation=Operation.ADDITIVE, value=delta_atk, source=ModifierSource.SKILL, duration_turns=duration_turns)
        ],
    )

# ----- Unit Templates -----

def hero_template() -> Unit:
    """A standard player-controlled hero unit."""
    return Unit(
        id="u.player.hero", side=Side.PLAYER, name="Hero", pos=(0, 0),
        stats=StatBlock(base={
            StatName.HP: 10, StatName.AP: 2, StatName.ATK: 3, StatName.DEF: 2,
            StatName.MOV: 4, StatName.RNG: 1, StatName.CRIT: 5, StatName.INIT: 12
        }),
        ap_left=2
    )

def archer_template() -> Unit:
    """A standard player-controlled archer unit."""
    return Unit(
        id="u.player.archer", side=Side.PLAYER, name="Archer", pos=(0, 0),
        stats=StatBlock(base={
            StatName.HP: 9, StatName.AP: 2, StatName.ATK: 2, StatName.DEF: 1,
            StatName.MOV: 4, StatName.RNG: 2, StatName.CRIT: 5, StatName.INIT: 14
        }),
        ap_left=2
    )

def goblin_template() -> Unit:
    """A standard enemy goblin unit."""
    return Unit(
        id="u.enemy.goblin", side=Side.ENEMY, name="Goblin", pos=(0, 0),
        stats=StatBlock(base={
            StatName.HP: 8, StatName.AP: 2, StatName.ATK: 2, StatName.DEF: 1,
            StatName.MOV: 3, StatName.RNG: 1, StatName.CRIT: 0, StatName.INIT: 9
        }),
        ap_left=2
    )

# ----- Mission Templates -----

def simple_mission(units: list[Unit], width: int = 3, height: int = 3) -> Mission:
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
