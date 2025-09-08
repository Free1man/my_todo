from pydantic import BaseModel, Field

from .enums import Coord, Side, StatName
from .modifiers import StatBlock, StatModifier
from .skills import Aura, Injury, Item, Skill


class Unit(BaseModel):
    id: str = "unit.example"
    side: Side = Side.PLAYER
    name: str = "Unit"
    pos: Coord = (0, 0)
    stats: StatBlock = Field(
        default_factory=lambda: StatBlock(
            base={
                StatName.HP: 10,
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
    # Temporary buffs/debuffs applied by skills; decays each turn via engine.effects
    temp_mods: list[StatModifier] = Field(default_factory=list)
    auras: list[Aura] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    alive: bool = True
    ap_left: int = 0
    skill_cooldowns: dict[str, int] = Field(default_factory=dict)
    skill_charges: dict[str, int] = Field(default_factory=dict)
