from pydantic import BaseModel, Field

from .enums import SkillKind, SkillTarget
from .modifiers import StatModifier


class Skill(BaseModel):
    id: str
    name: str
    kind: SkillKind
    ap_cost: int = 0
    range: int = 0
    target: SkillTarget = SkillTarget.NONE
    cooldown: int = 0
    charges: int | None = None
    apply_mods: list[StatModifier] = Field(default_factory=list)
    passive_mods: list[StatModifier] = Field(default_factory=list)


class Item(BaseModel):
    id: str = "item.example"
    name: str = "Item"
    mods: list[StatModifier] = Field(default_factory=list)


class Injury(BaseModel):
    id: str
    name: str
    mods: list[StatModifier] = Field(default_factory=list)


class Aura(BaseModel):
    id: str
    name: str
    radius: int
    mods: list[StatModifier] = Field(default_factory=list)
    owner_unit_id: str | None = None
