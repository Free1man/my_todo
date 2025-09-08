from __future__ import annotations

from ...models.api import EndTurnAction
from ...models.enums import ActionLogResult
from ...models.session import TBSSession
from ..logging.logger import log_event
from ..systems.turn import end_turn
from .base import ActionHandler


class EndTurnHandler(ActionHandler):
    action_type = EndTurnAction

    def evaluate(self, mission, action: EndTurnAction):
        return True, "ok"

    def apply(self, sess: TBSSession, action: EndTurnAction):
        end_turn(sess.mission)
        log_event(sess, action, ActionLogResult.APPLIED)
        return TBSSession(id=sess.id, mission=sess.mission)
