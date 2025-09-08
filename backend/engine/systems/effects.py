from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.modifiers import StatModifier
    from ...models.units import Unit

from pydantic import BaseModel

from ...models.enums import StatName


class InjuryFromMods(BaseModel):
    id: str = "inj.temp"
    name: str = "Temporary Effect"
    mods: list[StatModifier]

    def __init__(self, mods: list[StatModifier]):
        super().__init__(mods=mods)


def attach_temp_mods(u: Unit, mods: list[StatModifier]) -> None:
    inj = InjuryFromMods(mods)
    u.injuries.append(inj)


def read_max_hp_tag(unit: Unit) -> int | None:
    for tag in unit.tags:
        if isinstance(tag, str) and tag.startswith("MAX_HP="):
            try:
                return int(tag.split("=", 1)[1])
            except Exception:
                return None
    return None


def ensure_max_hp_tag(unit: Unit) -> None:
    if not any(isinstance(t, str) and t.startswith("MAX_HP=") for t in unit.tags):
        base_hp = unit.stats.base.get(StatName.HP, 0)
        unit.tags.append(f"MAX_HP={base_hp}")


def decay_temporary_mods(u: Unit) -> None:
    kept = []
    for inj in u.injuries:
        new_mods = []
        for m in inj.mods:
            if m.duration_turns is None:
                new_mods.append(m)
            elif m.duration_turns > 1:
                m.duration_turns -= 1
                new_mods.append(m)
        if new_mods:
            inj.mods = new_mods
            kept.append(inj)
    u.injuries = kept
