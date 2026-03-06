# tests/integration/utils/data.py
from __future__ import annotations

from backend.models.enums import (
    GoalKind,
    ModifierSource,
    Operation,
    Side,
    SkillKind,
    SkillTarget,
    StatName,
    Terrain,
)
from backend.models.map import MapGrid, Tile
from backend.models.mission import Mission, MissionGoal, TurnState
from backend.models.modifiers import StatBlock, StatModifier
from backend.models.skills import (
    ApplyModifierEffect,
    DamageEffect,
    HealEffect,
    Item,
    Skill,
)
from backend.models.units import BattleUnitState, Unit, UnitTemplate

# ----- Item Templates -----


def iron_sword_template() -> Item:
    """A basic melee weapon."""
    return Item(
        id="item.sword.iron",
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


def short_bow_template() -> Item:
    """A basic ranged weapon that increases range."""
    return Item(
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
        effects=[HealEffect(amount=amount)],
    )


def weaken_attack_skill_template(
    delta_atk: int = -2, *, duration_turns: int = 2
) -> Skill:
    """Debuff that reduces enemy ATK for a few turns (default 2). Costs 1 AP, range 3, target enemy."""
    return Skill(
        id="skill.debuff.weaken",
        name="Weaken",
        kind=SkillKind.ACTIVE,
        ap_cost=1,
        range=3,
        target=SkillTarget.ENEMY_UNIT,
        cooldown=0,
        effects=[
            ApplyModifierEffect(
                modifier=StatModifier(
                    stat=StatName.ATK,
                    operation=Operation.ADDITIVE,
                    value=delta_atk,
                    source=ModifierSource.SKILL,
                    duration_turns=duration_turns,
                )
            )
        ],
    )


def fireball_skill_template(
    power: int = 3,
    *,
    rng: int = 3,
    ap_cost: int = 1,
    area_offsets: list[tuple[int, int]] | None = None,
) -> Skill:
    """A TILE-target AOE that deals flat damage (negative HP) within an area around the target tile.
    Shape is defined on the skill itself; if no offsets are provided, engine defaults to 3x3.
    """
    return Skill(
        id="skill.fireball",
        name="Fireball",
        kind=SkillKind.ACTIVE,
        ap_cost=ap_cost,
        range=rng,
        target=SkillTarget.TILE,
        cooldown=0,
        area_offsets=area_offsets or [],
        effects=[DamageEffect(amount=power)],
    )


# ----- Unit Templates -----


def _make_unit(
    *,
    uid: str,
    side: Side,
    name: str,
    pos: tuple[int, int],
    stats: dict[StatName, int],
    ap_left: int = 2,
) -> Unit:
    return Unit(
        id=uid,
        template=UnitTemplate(
            side=side,
            name=name,
            stats=StatBlock(base=stats),
        ),
        state=BattleUnitState(
            pos=pos,
            hp=stats.get(StatName.MAX_HP, stats.get(StatName.HP, 0)),
            ap_left=ap_left,
        ),
    )


def hero_template() -> Unit:
    """A standard player-controlled hero unit."""
    return _make_unit(
        uid="u.player.hero",
        side=Side.PLAYER,
        name="Hero",
        pos=(0, 0),
        stats={
            StatName.MAX_HP: 10,
            StatName.AP: 2,
            StatName.ATK: 3,
            StatName.DEF: 2,
            StatName.MOV: 4,
            StatName.RNG: 1,
            StatName.CRIT: 5,
            StatName.INIT: 12,
        },
    )


def archer_template() -> Unit:
    """A standard player-controlled archer unit."""
    return _make_unit(
        uid="u.player.archer",
        side=Side.PLAYER,
        name="Archer",
        pos=(0, 0),
        stats={
            StatName.MAX_HP: 9,
            StatName.AP: 2,
            StatName.ATK: 2,
            StatName.DEF: 1,
            StatName.MOV: 4,
            StatName.RNG: 2,
            StatName.CRIT: 5,
            StatName.INIT: 14,
        },
    )


def goblin_template() -> Unit:
    """A standard enemy goblin unit."""
    return _make_unit(
        uid="u.enemy.goblin",
        side=Side.ENEMY,
        name="Goblin",
        pos=(0, 0),
        stats={
            StatName.MAX_HP: 8,
            StatName.AP: 2,
            StatName.ATK: 2,
            StatName.DEF: 1,
            StatName.MOV: 3,
            StatName.RNG: 1,
            StatName.CRIT: 0,
            StatName.INIT: 9,
        },
    )


# ----- Mission Templates -----


def simple_mission(units: list[Unit], width: int = 3, height: int = 3) -> Mission:
    grid = MapGrid(
        width=width,
        height=height,
        tiles=[
            [Tile(terrain=Terrain.PLAIN) for _ in range(width)] for _ in range(height)
        ],
    )
    occupied: set[tuple[int, int]] = set()
    unit_map: dict[str, Unit] = {}
    for unit in units:
        placed = unit.model_copy(deep=True)
        if placed.state.pos in occupied:
            for y in range(height):
                for x in range(width):
                    if (x, y) not in occupied:
                        placed.state.pos = (x, y)
                        break
                else:
                    continue
                break
        occupied.add(placed.state.pos)
        unit_map[placed.id] = placed
    return Mission(
        id="m.test",
        name="Test Mission",
        map=grid,
        units=unit_map,
        goals=[MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)],
        turn_state=TurnState(),
    )
