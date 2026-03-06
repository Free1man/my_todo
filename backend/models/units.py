from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import Coord, Side, StatName
from .modifiers import StatBlock, StatModifier
from .skills import Aura, Injury, Item, Skill


class UnitTemplate(BaseModel):
    side: Side = Side.PLAYER
    name: str = "Unit"
    stats: StatBlock = Field(
        default_factory=lambda: StatBlock(
            base={
                StatName.MAX_HP: 10,
                StatName.AP: 2,
                StatName.ATK: 3,
                StatName.DEF: 1,
                StatName.MOV: 4,
                StatName.RNG: 1,
                StatName.CRIT: 5,
                StatName.INIT: 10,
            }
        )
    )
    items: list[Item] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)
    auras: list[Aura] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class BattleUnitState(BaseModel):
    pos: Coord = (0, 0)
    hp: int = 10
    ap_left: int = 0
    # Temporary buffs/debuffs applied by skills; decays each turn via engine.effects
    temp_mods: list[StatModifier] = Field(default_factory=list)
    skill_cooldowns: dict[str, int] = Field(default_factory=dict)
    skill_charges: dict[str, int] = Field(default_factory=dict)


class Unit(BaseModel):
    id: str = "unit.example"
    template: UnitTemplate = Field(default_factory=UnitTemplate)
    state: BattleUnitState = Field(default_factory=BattleUnitState)
