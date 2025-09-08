from __future__ import annotations

from typing import TYPE_CHECKING

from backend.engine.systems import victory

if TYPE_CHECKING:
    from ..models.session import TBSSession
    from .actions.base import Registry

from ..models.api import (
    Action,
    AttackAction,
    EndTurnAction,
    EvaluateResponse,
    LegalAction,
    LegalActionsResponse,
    MoveAction,
)
from ..models.enums import StatName
from .actions.attack import AttackHandler
from .actions.end_turn import EndTurnHandler
from .actions.move import MoveHandler
from .actions.skill import (
    SkillHandler,
    enumerate_legal as enumerate_skill_legal,
)
from .logging.logger import log_error, log_illegal
from .systems import combat, pathfinding, stats, turn

default_handlers: Registry = {
    MoveHandler.action_type: MoveHandler(),
    AttackHandler.action_type: AttackHandler(),
    SkillHandler.action_type: SkillHandler(),
    EndTurnHandler.action_type: EndTurnHandler(),
}


class TBSEngine:
    def __init__(self, handlers: Registry | None = None):
        self.handlers: Registry = handlers or default_handlers

    def evaluate(self, sess: TBSSession, action: Action) -> EvaluateResponse:
        h = self.handlers.get(type(action))
        if not h:
            return EvaluateResponse(legal=False, explanation="unknown action")
        ok, why = h.evaluate(sess.mission, action)
        return EvaluateResponse(legal=ok, explanation=why)

    def process_action(self, sess: TBSSession, action: Action):
        ev = self.evaluate(sess, action)
        if not ev.legal:
            log_illegal(sess, action, ev.explanation)
            return ev, None
        try:
            new_sess = self.handlers[type(action)].apply(sess, action)
            return ev, new_sess
        except Exception as e:
            log_error(sess, action, e)
            raise

    def apply(self, sess: TBSSession, action: Action) -> TBSSession:
        return self.handlers[type(action)].apply(sess, action)

    def list_legal_actions(
        self, sess: TBSSession, *, explain: bool = False
    ) -> LegalActionsResponse:
        m = sess.mission
        out: list[LegalAction] = []
        cu = m.units.get(m.current_unit_id)
        if not cu or not cu.alive:
            return LegalActionsResponse(actions=out)

        ok, why = self.handlers[EndTurnAction].evaluate(m, EndTurnAction())
        if ok:
            out.append(LegalAction(action=EndTurnAction(), explanation=why))

        if cu.ap_left >= 1:
            for dst in pathfinding.reachable_tiles(m, cu):
                if dst != cu.pos:
                    act = MoveAction(unit_id=cu.id, to=dst)
                    ok, why = self.handlers[MoveAction].evaluate(m, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))

        if cu.ap_left >= 1:
            rng = stats.eff_stat(m, cu, StatName.RNG)
            for other in m.units.values():
                if (
                    other.alive
                    and other.id != cu.id
                    and pathfinding.manhattan(cu.pos, other.pos) <= rng
                ):
                    act = AttackAction(attacker_id=cu.id, target_id=other.id)
                    ok, why = self.handlers[AttackAction].evaluate(m, act)
                    if ok:
                        evaluation = (
                            combat.evaluate_attack(m, act.attacker_id, act.target_id)
                            if explain
                            else None
                        )
                        out.append(
                            LegalAction(
                                action=act, explanation=why, evaluation=evaluation
                            )
                        )

        out.extend(enumerate_skill_legal(m, cu, self.handlers, explain))
        return LegalActionsResponse(actions=out)

    def initialize_mission(self, mission):
        turn.initialize_mission(mission)

    def check_victory_conditions(self, sess):
        return victory.check(sess)
