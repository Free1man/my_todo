from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.mission import Mission
    from ...models.units import Unit

from ...models.enums import Side, StatName
from . import stats
from .effects import decay_temporary_mods


def _tick_unit_turn_state(u: Unit) -> None:
    """Advance cooldowns and temporary effects for a single unit turn."""
    for sid in list(u.state.skill_cooldowns.keys()):
        remaining = u.state.skill_cooldowns.get(sid, 0)
        if remaining <= 1:
            u.state.skill_cooldowns.pop(sid, None)
        else:
            u.state.skill_cooldowns[sid] = remaining - 1
    decay_temporary_mods(u)


def _begin_unit_turn(mission: Mission, u: Unit, *, tick_state: bool) -> None:
    if tick_state:
        _tick_unit_turn_state(u)
    u.state.ap_left = stats.eff_stat(mission, u, StatName.AP)
    mission.turn_state.side_to_move = u.template.side


def recompute_initiative_order(mission: Mission) -> None:
    living: list[Unit] = mission.living_units()
    living.sort(
        key=lambda u: (
            -stats.eff_stat(mission, u, StatName.INIT),
            0 if u.template.side == Side.PLAYER else 1,
            u.template.name,
        )
    )
    mission.turn_state.initiative_order = [u.id for u in living]
    mission.turn_state.current_unit_id = (
        mission.turn_state.initiative_order[0] if living else None
    )
    if mission.turn_state.current_unit_id:
        mission.turn_state.side_to_move = mission.units[
            mission.turn_state.current_unit_id
        ].template.side


def end_turn(mission: Mission) -> None:
    order = mission.turn_state.initiative_order or []
    if not order:
        recompute_initiative_order(mission)
        order = mission.turn_state.initiative_order
    if not order:
        mission.turn_state.current_unit_id = None
        return

    try:
        idx = (
            order.index(mission.turn_state.current_unit_id)
            if mission.turn_state.current_unit_id in order
            else -1
        )
    except ValueError:
        idx = -1

    n = len(order)
    if n == 0:
        mission.turn_state.current_unit_id = None
        return

    for step in range(1, n + 1):
        next_idx = (idx + step) % n
        candidate_id = order[next_idx]
        cu = mission.units.get(candidate_id)
        if cu and cu.state.alive:
            if next_idx <= idx:
                mission.turn_state.turn += 1
            mission.turn_state.current_unit_id = candidate_id
            _begin_unit_turn(mission, cu, tick_state=True)
            break
    else:
        mission.turn_state.current_unit_id = None


def initialize_mission(mission: Mission) -> None:
    requested_cursor = mission.turn_state.current_unit_id
    recompute_initiative_order(mission)
    if requested_cursor and requested_cursor in mission.turn_state.initiative_order:
        idx = mission.turn_state.initiative_order.index(requested_cursor)
        mission.turn_state.initiative_order = (
            mission.turn_state.initiative_order[idx:]
            + mission.turn_state.initiative_order[:idx]
        )
    mission.turn_state.current_unit_id = (
        mission.turn_state.initiative_order[0]
        if mission.turn_state.initiative_order
        else None
    )
    if mission.turn_state.current_unit_id:
        u = mission.units.get(mission.turn_state.current_unit_id)
        if u and u.state.alive:
            _begin_unit_turn(mission, u, tick_state=False)
