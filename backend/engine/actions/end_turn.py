from __future__ import annotations

from typing import TYPE_CHECKING

from ...models.api import EndTurnAction
from ...models.enums import ActionLogResult
from ..logging.logger import log_event
from ..systems.turn import end_turn
from .base import ActionHandler

if TYPE_CHECKING:
    from ..runtime import RuntimeSession


class EndTurnHandler(ActionHandler):
    action_type = EndTurnAction

    def evaluate(self, mission, action: EndTurnAction):
        if mission.current_unit() is None:
            return False, "no active unit"
        return True, "ok"

    def apply(self, sess: RuntimeSession, action: EndTurnAction):
        end_turn(sess.mission)
        log_event(sess, action, ActionLogResult.APPLIED)
        return sess
