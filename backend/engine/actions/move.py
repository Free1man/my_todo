from __future__ import annotations

from ...models.api import MoveAction
from ...models.enums import ActionLogResult
from ...models.session import TBSSession
from ..logging.logger import log_event
from ..systems import pathfinding
from .base import ActionHandler


class MoveHandler(ActionHandler):
    action_type = MoveAction

    def evaluate(self, mission, action: MoveAction):
        u = mission.units.get(action.unit_id)
        if not u:
            return False, "unknown unit"
        if not u.alive or mission.current_unit_id != u.id:
            return False, "unit cannot act"
        if u.ap_left < 1:
            return False, "no AP left"
        if action.to == u.pos:
            return False, "already at destination"
        if not mission.map.in_bounds(action.to):
            return False, "destination out of bounds"
        if not mission.map.tile(action.to).walkable:
            return False, "destination not walkable"
        if any(
            v.alive and v.id != u.id and v.pos == action.to
            for v in mission.units.values()
        ):
            return False, "destination occupied"
        return (
            (True, "ok")
            if pathfinding.can_reach(mission, u, action.to)
            else (False, "cannot reach")
        )

    def apply(self, sess: TBSSession, action: MoveAction):
        m = sess.mission
        u = m.units[action.unit_id]
        u.pos = action.to
        u.ap_left -= 1
        log_event(sess, action, ActionLogResult.APPLIED)
        return TBSSession(id=sess.id, mission=m)
