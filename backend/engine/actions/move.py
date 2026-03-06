from __future__ import annotations

from typing import TYPE_CHECKING

from ...models.api import MoveAction
from ...models.enums import ActionLogResult
from ..logging.logger import log_event
from ..rules import require_ap, require_current_actor, require_unit
from ..systems import pathfinding
from .base import ActionHandler

if TYPE_CHECKING:
    from ..runtime import RuntimeSession


class MoveHandler(ActionHandler):
    action_type = MoveAction

    def evaluate(self, mission, action: MoveAction):
        u, reason = require_unit(mission, action.unit_id)
        if reason:
            return False, reason
        if reason := require_current_actor(mission, u):
            return False, reason
        if reason := require_ap(u, 1):
            return False, reason
        if action.to == u.state.pos:
            return False, "already at destination"
        if not mission.map.in_bounds(action.to):
            return False, "destination out of bounds"
        if not mission.map.tile(action.to).walkable:
            return False, "destination not walkable"
        if mission.occupied(action.to, exclude_unit_id=u.id):
            return False, "destination occupied"
        return (
            (True, "ok")
            if pathfinding.can_reach(mission, u, action.to)
            else (False, "cannot reach")
        )

    def apply(self, sess: RuntimeSession, action: MoveAction):
        m = sess.mission
        u = m.units[action.unit_id]
        u.state.pos = action.to
        u.state.ap_left -= 1
        m.invalidate_cache()
        log_event(sess, action, ActionLogResult.APPLIED)
        return sess
