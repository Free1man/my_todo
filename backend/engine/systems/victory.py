from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime import RuntimeMission

from ...models.enums import GoalKind, MissionStatus, Side


def check(mission: RuntimeMission) -> MissionStatus:
    if mission.turn_state.status != MissionStatus.IN_PROGRESS:
        return mission.turn_state.status

    for goal in mission.goals:
        if goal.kind == GoalKind.ELIMINATE_ALL_ENEMIES:
            if not mission.living_units_for(Side.ENEMY):
                return MissionStatus.VICTORY
        elif goal.kind == GoalKind.SURVIVE_TURNS and mission.turn_state.turn >= (
            goal.survive_turns or 0
        ):
            return MissionStatus.VICTORY

    if not mission.living_units_for(Side.PLAYER):
        return MissionStatus.DEFEAT

    return MissionStatus.IN_PROGRESS
