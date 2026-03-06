from __future__ import annotations

from typing import TYPE_CHECKING

from backend.engine.systems import victory

if TYPE_CHECKING:
    from ..models.mission import Mission
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
from .runtime import mission_from_dto, mission_to_dto, session_from_dto, session_to_dto
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
        runtime = session_from_dto(sess)
        ok, why = h.evaluate(runtime.mission, action)
        return EvaluateResponse(legal=ok, explanation=why)

    def process_action(self, sess: TBSSession, action: Action):
        ev = self.evaluate(sess, action)
        if not ev.legal:
            log_illegal(sess, action, ev.explanation)
            return ev, None
        try:
            new_sess = self.apply(sess, action)
            return ev, new_sess
        except Exception as e:
            log_error(sess, action, e)
            raise

    def apply(self, sess: TBSSession, action: Action) -> TBSSession:
        runtime = session_from_dto(sess)
        updated = self.handlers[type(action)].apply(runtime, action)
        updated.mission.turn_state.status = victory.check(updated.mission)
        return session_to_dto(updated)

    def list_legal_actions(
        self, sess: TBSSession, *, explain: bool = False
    ) -> LegalActionsResponse:
        m = session_from_dto(sess).mission
        out: list[LegalAction] = []
        m.turn_state.status = victory.check(m)
        cu = m.current_unit()
        if not cu:
            return LegalActionsResponse(actions=out)

        ok, why = self.handlers[EndTurnAction].evaluate(m, EndTurnAction())
        if ok:
            out.append(LegalAction(action=EndTurnAction(), explanation=why))

        if cu.state.ap_left >= 1:
            for dst in pathfinding.reachable_tiles(m, cu):
                if dst != cu.state.pos:
                    act = MoveAction(unit_id=cu.id, to=dst)
                    ok, why = self.handlers[MoveAction].evaluate(m, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))

        if cu.state.ap_left >= 1:
            rng = stats.eff_stat(m, cu, StatName.RNG)
            for other in m.living_units():
                if other.id == cu.id:
                    continue
                if pathfinding.manhattan(cu.state.pos, other.state.pos) <= rng:
                    act = AttackAction(attacker_id=cu.id, target_id=other.id)
                    evaluation = (
                        combat.evaluate_attack(m, act.attacker_id, act.target_id)
                        if explain
                        else None
                    )
                    if evaluation is not None and evaluation.effects:
                        effect = evaluation.effects[0]
                        predicted_damage = int(evaluation.expected_damage)
                        hp_before = int(effect.before or 0)
                        hp_after = int(effect.after or 0)
                        would_defeat = "yes" if hp_after == 0 else "no"
                        explanation = (
                            f"ok (predicted_damage={predicted_damage}, "
                            f"target_hp_before={hp_before}, "
                            f"target_hp_after={hp_after}, "
                            f"would_defeat={would_defeat})"
                        )
                    else:
                        dmg, hp_before, hp_after, kills = combat.quick_attack_preview(
                            m, cu, other
                        )
                        explanation = (
                            f"ok (predicted_damage={dmg}, "
                            f"target_hp_before={hp_before}, "
                            f"target_hp_after={hp_after}, "
                            f"would_defeat={'yes' if kills else 'no'})"
                        )
                    out.append(
                        LegalAction(
                            action=act,
                            explanation=explanation,
                            evaluation=evaluation,
                        )
                    )

        out.extend(enumerate_skill_legal(m, cu, self.handlers, explain))
        return LegalActionsResponse(actions=out)

    def initialize_mission(self, mission: Mission) -> Mission:
        runtime = mission_from_dto(mission)
        turn.initialize_mission(runtime)
        runtime.turn_state.status = victory.check(runtime)
        return mission_to_dto(runtime)

    def check_victory_conditions(self, sess: TBSSession):
        return victory.check(session_from_dto(sess).mission)
