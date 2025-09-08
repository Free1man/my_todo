from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.mission import Mission
    from ...models.modifiers import StatModifier
    from ...models.units import Unit

from pydantic import BaseModel

from ...models.enums import ModifierSource, Operation, StatName, TermKind
from ...models.evaluation import StatBreakdown, StatTerm
from .pathfinding import manhattan


class EffStat(BaseModel):
    value: float
    breakdown: StatBreakdown


def _map_source_to_kind(src: ModifierSource | None) -> TermKind:
    if src == ModifierSource.ITEM:
        return TermKind.ITEM
    if src == ModifierSource.AURA:
        return TermKind.BUFF
    if src == ModifierSource.MAP:
        return TermKind.TERRAIN
    if src == ModifierSource.INJURY:
        return TermKind.DEBUFF
    if src == ModifierSource.SKILL:
        return TermKind.SKILL
    return TermKind.CONTEXT


def eff_stat_with_trace(mission: Mission, u: Unit, stat: StatName) -> EffStat:
    base_val = u.stats.base.get(stat, 0)

    # Collect modifiers
    all_mods: list[StatModifier] = []
    for it in u.items:
        all_mods.extend(it.mods)
    for inj in u.injuries:
        all_mods.extend(inj.mods)
    for a in u.auras:
        all_mods.extend(a.mods)
    for other in mission.units.values():
        if not other.alive or other.id == u.id:
            continue
        if not other.auras:
            continue
        d = manhattan(u.pos, other.pos)
        for a in other.auras:
            if d <= (a.radius or 0):
                all_mods.extend(a.mods)
    all_mods.extend(mission.map.tile(u.pos).mods)
    for s in u.skills:
        all_mods.extend(s.passive_mods)
    all_mods.extend(mission.global_mods)

    add_flat = 0
    mul = 1.0
    override: int | None = None
    terms: list[StatTerm] = []

    for m in all_mods:
        if m.stat != stat:
            continue
        kind = _map_source_to_kind(m.source)
        if m.operation == Operation.ADDITIVE:
            add_flat += m.value
            terms.append(
                StatTerm(
                    kind=kind,
                    source=m.source.value if m.source else "context",
                    op=Operation.ADDITIVE,
                    value=float(m.value),
                )
            )
        elif m.operation == Operation.MULTIPLICATIVE:
            mul *= 1.0 + (m.value / 100.0)
            terms.append(
                StatTerm(
                    kind=kind,
                    source=m.source.value if m.source else "context",
                    op=Operation.MULTIPLICATIVE,
                    value=float(m.value) / 100.0,
                )
            )
        elif m.operation == Operation.OVERRIDE:
            override = m.value
            delta = float(m.value - base_val)
            terms.append(
                StatTerm(
                    kind=kind,
                    source=m.source.value if m.source else "context",
                    op=Operation.ADDITIVE,
                    value=delta,
                    note="override",
                )
            )

    base_applied = override if override is not None else base_val
    result = max(int(base_applied * mul) + add_flat, 0)

    bd = StatBreakdown(
        name=stat.value.lower(),
        base=float(base_val),
        terms=terms,
        result=float(result),
    )
    return EffStat(value=float(result), breakdown=bd)


def eff_stat(mission: Mission, u: Unit, stat: StatName) -> int:
    value = u.stats.base.get(stat, 0)

    def apply_mods(mods: list[StatModifier], cur: int) -> int:
        add = 0
        mul = 1.0
        override: int | None = None
        for m in mods:
            if m.stat != stat:
                continue
            if m.operation == Operation.ADDITIVE:
                add += m.value
            elif m.operation == Operation.MULTIPLICATIVE:
                mul *= 1.0 + (m.value / 100.0)
            elif m.operation == Operation.OVERRIDE:
                override = m.value
        base = cur if override is None else override
        return max(int(base * mul) + add, 0)

    all_mods: list[StatModifier] = []
    for it in u.items:
        all_mods.extend(it.mods)
    for inj in u.injuries:
        all_mods.extend(inj.mods)
    for a in u.auras:
        all_mods.extend(a.mods)
    for other in mission.units.values():
        if not other.alive or other.id == u.id:
            continue
        if not other.auras:
            continue
        from .pathfinding import manhattan as _mh

        d = _mh(u.pos, other.pos)
        for a in other.auras:
            if d <= (a.radius or 0):
                all_mods.extend(a.mods)

    all_mods.extend(mission.map.tile(u.pos).mods)
    for s in u.skills:
        all_mods.extend(s.passive_mods)
    all_mods.extend(mission.global_mods)

    return apply_mods(all_mods, value)
