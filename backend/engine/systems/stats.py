from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.modifiers import StatModifier
    from ..runtime import RuntimeMission, RuntimeUnit

from pydantic import BaseModel

from ...models.enums import ModifierSource, Operation, StatName
from ...models.evaluation import StatBreakdown, StatTerm
from .pathfinding import manhattan


class EffStat(BaseModel):
    value: float
    breakdown: StatBreakdown


def _source_kind(src: ModifierSource | None) -> ModifierSource:
    return src or ModifierSource.CONTEXT


def _collect_modifiers(
    mission: RuntimeMission, u: RuntimeUnit
) -> tuple[StatModifier, ...]:
    cached = mission.cache.modifiers.get(u.id)
    if cached is not None:
        return cached

    all_mods: list[StatModifier] = []
    for it in u.template.items:
        all_mods.extend(it.mods)
    for inj in u.template.injuries:
        all_mods.extend(inj.mods)
    for a in u.template.auras:
        all_mods.extend(a.mods)
    # Temporary modifiers applied by skills
    all_mods.extend(u.state.temp_mods)
    for other in mission.living_units():
        if other.id == u.id:
            continue
        if not other.template.auras:
            continue
        d = manhattan(u.state.pos, other.state.pos)
        for a in other.template.auras:
            if d <= (a.radius or 0):
                all_mods.extend(a.mods)
    all_mods.extend(mission.map.tile(u.state.pos).mods)
    for s in u.template.skills:
        all_mods.extend(s.passive_mods)
    all_mods.extend(mission.global_mods)
    cached = tuple(all_mods)
    mission.cache.modifiers[u.id] = cached
    return cached


def _apply_stat_modifiers(
    base_val: int,
    stat: StatName,
    mods: list[StatModifier],
    *,
    trace: bool,
) -> tuple[int, list[StatTerm]]:
    add_flat = 0
    mul = 1.0
    override: int | None = None
    terms: list[StatTerm] = []

    for m in mods:
        if m.stat != stat:
            continue
        if m.operation == Operation.ADDITIVE:
            add_flat += m.value
            if trace:
                kind = _source_kind(m.source)
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
            if trace:
                kind = _source_kind(m.source)
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
            if trace:
                kind = _source_kind(m.source)
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
    return max(int(base_applied * mul) + add_flat, 0), terms


def _base_stat_value(mission: RuntimeMission, u: RuntimeUnit, stat: StatName) -> int:
    if stat == StatName.HP:
        return u.state.hp
    return u.template.stats.base.get(stat, 0)


def eff_stat_with_extra_mods(
    mission: RuntimeMission,
    u: RuntimeUnit,
    stat: StatName,
    extra_mods: list[StatModifier] | tuple[StatModifier, ...],
    *,
    trace: bool = False,
) -> int | EffStat:
    base_val = _base_stat_value(mission, u, stat)
    result, terms = _apply_stat_modifiers(
        base_val,
        stat,
        [*_collect_modifiers(mission, u), *extra_mods],
        trace=trace,
    )
    if not trace:
        return result

    bd = StatBreakdown(
        name=stat.value.lower(),
        base=float(base_val),
        terms=terms,
        result=float(result),
    )
    return EffStat(value=float(result), breakdown=bd)


def eff_stat_with_trace(
    mission: RuntimeMission, u: RuntimeUnit, stat: StatName
) -> EffStat:
    traced = eff_stat_with_extra_mods(mission, u, stat, (), trace=True)
    mission.cache.stats[(u.id, stat)] = int(traced.value)
    return traced


def eff_stat(mission: RuntimeMission, u: RuntimeUnit, stat: StatName) -> int:
    cached = mission.cache.stats.get((u.id, stat))
    if cached is not None:
        return cached
    value = _base_stat_value(mission, u, stat)
    result, _ = _apply_stat_modifiers(
        value, stat, _collect_modifiers(mission, u), trace=False
    )
    mission.cache.stats[(u.id, stat)] = result
    return result
