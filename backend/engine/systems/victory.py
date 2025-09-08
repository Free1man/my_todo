from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.session import TBSSession

from ...models.enums import GoalKind, MissionStatus, Side


def check(sess: TBSSession) -> MissionStatus:
    mission = sess.mission
    if mission.status != MissionStatus.IN_PROGRESS:
        return mission.status

    for goal in mission.goals:
        if goal.kind == GoalKind.ELIMINATE_ALL_ENEMIES:
            if not any(
                u.alive and u.side == Side.ENEMY for u in mission.units.values()
            ):
                return MissionStatus.VICTORY
        elif goal.kind == GoalKind.SURVIVE_TURNS and mission.turn >= (
            goal.survive_turns or 0
        ):
            return MissionStatus.VICTORY

    if not any(u.alive and u.side == Side.PLAYER for u in mission.units.values()):
        return MissionStatus.DEFEAT

    return MissionStatus.IN_PROGRESS
