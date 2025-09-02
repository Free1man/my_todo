# tests/integration/templates.py
from __future__ import annotations
from backend.models.common import (
    Item,
    Unit,
    StatBlock,
    StatName,
    Side,
    Operation,
    ModifierSource,
    StatModifier,
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
