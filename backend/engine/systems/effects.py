from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.modifiers import StatModifier
    from ...models.units import Unit


def decay_temporary_mods(u: Unit) -> None:
    """Reduce duration_turns on temp_mods; drop expired; keep None (permanent) and >1 (decremented)."""
    if not u.state.temp_mods:
        u.state.temp_mods = []
        return
    new_mods: list[StatModifier] = []
    for m in u.state.temp_mods:
        if m.duration_turns is None:
            new_mods.append(m)
        elif m.duration_turns > 1:
            m.duration_turns -= 1
            new_mods.append(m)
        # else: drop when it reaches 0 or 1 turns elapsed to 0
    u.state.temp_mods = new_mods
