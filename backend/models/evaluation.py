from typing import Literal

from pydantic import BaseModel, Field

from .enums import Op, TermKind


class StatTerm(BaseModel):
    kind: TermKind
    source: str
    op: Op
    value: float
    note: str | None = None


class StatBreakdown(BaseModel):
    name: str
    base: float
    terms: list[StatTerm] = Field(default_factory=list)
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
    vulnerability_mults: list[ResistEntry] = Field(default_factory=list)
    attacker_damage_mults: list[StatTerm] = Field(default_factory=list)
    final_before_crit: float
    crit_chance: float
    crit_mult: float
    crit_expected: float
    block_flat: float
    block_mult: float
    final_after_block: float
    min_cap: float | None = 1.0
    max_cap: float | None = None
    final_capped: float
    immune: bool = False


class HitChanceBreakdown(BaseModel):
    accuracy: StatBreakdown
    evasion: StatBreakdown
    base: float
    mods: list[StatTerm] = Field(default_factory=list)
    result: float


class ActionEvaluation(BaseModel):
    action_type: Literal["attack", "skill", "item", "wait"] = "attack"
    attacker_id: str
    target_id: str | None = None
    ap_cost: int
    summary: str
    expected_damage: float
    min_damage: float
    max_damage: float
    damage: DamageBreakdown | None = None
    hit: HitChanceBreakdown | None = None
    legality_ok: bool = True
    illegal_reasons: list[str] = Field(default_factory=list)
