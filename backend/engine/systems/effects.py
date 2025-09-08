from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.modifiers import StatModifier
    from ...models.units import Unit

from ...models.enums import StatName


def add_temp_mods(u: Unit, mods: list[StatModifier]) -> None:
    """Attach temporary modifiers to a unit; these decay via decay_temporary_mods."""
    if not mods:
        return
    u.temp_mods.extend(mods)


def ensure_max_hp_tag(unit: Unit) -> None:
    """Ensure the MAX_HP stat exists; initialize to current base HP if missing."""
    if StatName.MAX_HP not in unit.stats.base:
        unit.stats.base[StatName.MAX_HP] = unit.stats.base.get(StatName.HP, 0)


def decay_temporary_mods(u: Unit) -> None:
    """Reduce duration_turns on temp_mods; drop expired; keep None (permanent) and >1 (decremented)."""
    if not getattr(u, "temp_mods", None):
        u.temp_mods = []
        return
    new_mods: list[StatModifier] = []
    for m in u.temp_mods:
        if m.duration_turns is None:
            new_mods.append(m)
        elif m.duration_turns > 1:
            m.duration_turns -= 1
            new_mods.append(m)
        # else: drop when it reaches 0 or 1 turns elapsed to 0
    u.temp_mods = new_mods
