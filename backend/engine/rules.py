from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.enums import MissionStatus
from .systems.pathfinding import manhattan

if TYPE_CHECKING:
    from .runtime import RuntimeMission, RuntimeUnit


def require_in_progress(mission: RuntimeMission) -> str | None:
    if mission.turn_state.status != MissionStatus.IN_PROGRESS:
        return f"mission already {mission.turn_state.status.value}"
    return None


def require_unit(
    mission: RuntimeMission, unit_id: str, *, missing_reason: str = "unknown unit"
) -> tuple[RuntimeUnit | None, str | None]:
    unit = mission.units.get(unit_id)
    if unit is None:
        return None, missing_reason
    return unit, None


def require_current_actor(
    mission: RuntimeMission,
    unit: RuntimeUnit,
    *,
    reason: str = "unit cannot act",
) -> str | None:
    if not mission.is_current_actor(unit.id):
        return reason
    return None


def require_ap(unit: RuntimeUnit, amount: int) -> str | None:
    if unit.state.ap_left < amount:
        return "not enough AP" if amount > 1 else "no AP left"
    return None


def require_alive(
    unit: RuntimeUnit, *, reason: str = "target already down"
) -> str | None:
    if not unit.state.alive:
        return reason
    return None


def require_in_range(
    source: RuntimeUnit,
    target: tuple[int, int],
    limit: int,
    *,
    reason: str = "out of range",
) -> str | None:
    if manhattan(source.state.pos, target) > limit:
        return reason
    return None
