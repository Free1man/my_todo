from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .enums import Coord, DamageType, SkillKind, SkillTarget
from .modifiers import StatModifier


class DamageEffect(BaseModel):
    kind: Literal["damage"] = "damage"
    amount: int
    damage_type: DamageType = DamageType.MAGIC


class HealEffect(BaseModel):
    kind: Literal["heal"] = "heal"
    amount: int


class ApplyModifierEffect(BaseModel):
    kind: Literal["apply_modifier"] = "apply_modifier"
    modifier: StatModifier


SkillEffect = Annotated[
    DamageEffect | HealEffect | ApplyModifierEffect,
    Field(discriminator="kind"),
]


class Skill(BaseModel):
    id: str
    name: str
    kind: SkillKind
    ap_cost: int = 0
    range: int = 0
    target: SkillTarget = SkillTarget.NONE
    cooldown: int = 0
    charges: int | None = None
    area_offsets: list[Coord] = Field(default_factory=list)
    effects: list[SkillEffect] = Field(default_factory=list)
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
