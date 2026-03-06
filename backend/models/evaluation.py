from pydantic import BaseModel, Field

from .enums import ActionType, DamageType, ModifierSource, Operation


class StatTerm(BaseModel):
    kind: ModifierSource
    source: str
    op: Operation
    value: float
    note: str | None = None


class StatBreakdown(BaseModel):
    name: str
    base: float
    terms: list[StatTerm] = Field(default_factory=list)
    result: float


class ResistEntry(BaseModel):
    damage_type: DamageType
    mult: float
    source: str


class DamageBreakdown(BaseModel):
    damage_type: DamageType = DamageType.PHYSICAL
    attack: float
    defense: float
    effective_defense: float
    raw_damage: float
    crit_chance: float
    crit_mult: float
    final_damage: float
    formula: str


class HitChanceBreakdown(BaseModel):
    base: float
    result: float
    formula: str | None = None


class EffectPreview(BaseModel):
    target_id: str
    effect_kind: str
    stat: str | None = None
    before: float | None = None
    after: float | None = None
    delta: float | None = None
    duration_turns: int | None = None
    note: str | None = None


class ActionEvaluation(BaseModel):
    action_type: ActionType = ActionType.ATTACK
    attacker_id: str
    target_id: str | None = None
    ap_cost: int
    summary: str
    expected_damage: float
    min_damage: float
    max_damage: float
    damage: DamageBreakdown | None = None
    hit: HitChanceBreakdown | None = None
    effects: list[EffectPreview] = Field(default_factory=list)
    legality_ok: bool = True
    illegal_reasons: list[str] = Field(default_factory=list)
