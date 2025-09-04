from pydantic import BaseModel, Field

from .enums import ModifierSource, Operation, StatName


class StatModifier(BaseModel):
    stat: StatName
    operation: Operation
    value: int
    source: ModifierSource = ModifierSource.GLOBAL
    tag: str | None = None
    duration_turns: int | None = None  # None = persistent while source exists


class StatBlock(BaseModel):
    base: dict[StatName, int] = Field(default_factory=dict)
