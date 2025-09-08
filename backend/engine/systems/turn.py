from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.mission import Mission
    from ...models.units import Unit

from ...models.enums import Side, StatName
from . import stats
from .effects import decay_temporary_mods, ensure_max_hp_tag


def recompute_initiative_order(mission: Mission) -> None:
    living: list[Unit] = [u for u in mission.units.values() if u.alive]
    living.sort(
        key=lambda u: (
            -stats.eff_stat(mission, u, StatName.INIT),
            0 if u.side == Side.PLAYER else 1,
            u.name,
        )
    )
    mission.initiative_order = [u.id for u in living]
    mission.current_unit_id = mission.initiative_order[0] if living else None
    if mission.current_unit_id:
        mission.side_to_move = mission.units[mission.current_unit_id].side


def end_turn(mission: Mission) -> None:
    for u in mission.units.values():
        if not u.alive:
            continue
        for sid in list(u.skill_cooldowns.keys()):
            u.skill_cooldowns[sid] = max(0, u.skill_cooldowns.get(sid, 0) - 1)
        decay_temporary_mods(u)

    order = mission.initiative_order or []
    if not order:
        recompute_initiative_order(mission)
        order = mission.initiative_order
    if not order:
        mission.current_unit_id = None
        return

    try:
        idx = (
            order.index(mission.current_unit_id)
            if mission.current_unit_id in order
            else -1
        )
    except ValueError:
        idx = -1

    n = len(order)
    if n == 0:
        mission.current_unit_id = None
        return

    for step in range(1, n + 1):
        next_idx = (idx + step) % n
        candidate_id = order[next_idx]
        cu = mission.units.get(candidate_id)
        if cu and cu.alive:
            if next_idx <= idx:
                mission.turn += 1
            mission.current_unit_id = candidate_id
            cu.ap_left = stats.eff_stat(mission, cu, StatName.AP)
            mission.side_to_move = cu.side
            break
    else:
        mission.current_unit_id = None


def initialize_mission(mission: Mission) -> None:
    requested_cursor = mission.current_unit_id
    recompute_initiative_order(mission)
    for u in mission.units.values():
        with suppress(Exception):
            ensure_max_hp_tag(u)
    if requested_cursor and requested_cursor in mission.initiative_order:
        idx = mission.initiative_order.index(requested_cursor)
        mission.initiative_order = (
            mission.initiative_order[idx:] + mission.initiative_order[:idx]
        )
    mission.current_unit_id = (
        mission.initiative_order[0] if mission.initiative_order else None
    )
    if mission.current_unit_id:
        u = mission.units.get(mission.current_unit_id)
        if u and u.alive:
            u.ap_left = stats.eff_stat(mission, u, StatName.AP)
            mission.side_to_move = u.side
