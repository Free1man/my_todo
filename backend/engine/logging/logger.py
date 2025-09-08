from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.session import TBSSession

from ...events import ActionEvent, event_bus
from ...models.api import Action, ActionLogEntry
from ...models.enums import ActionLogResult


def actor_id(action: Action) -> str | None:
    from ...models.api import AttackAction, MoveAction, UseSkillAction

    if isinstance(action, MoveAction):
        return action.unit_id
    if isinstance(action, AttackAction):
        return action.attacker_id
    if isinstance(action, UseSkillAction):
        return action.unit_id
    return None


def log_event(
    sess: TBSSession,
    action: Action,
    result: ActionLogResult,
    message: str | None = None,
    attack_eval: dict | None = None,
) -> None:
    entry = ActionLogEntry(
        session_id=sess.id,
        turn=sess.mission.turn,
        actor_unit_id=actor_id(action),
        action=action,
        result=result,
        message=message,
        attack_eval=attack_eval,
    )
    event_bus.emit(
        ActionEvent(
            session_id=sess.id,
            turn=sess.mission.turn,
            actor_unit_id=actor_id(action),
            action=action,
            result=result,
            message=message,
            attack_eval=entry.attack_eval,
        )
    )


def log_illegal(sess: TBSSession, action: Action, explanation: str) -> None:
    log_event(sess, action, ActionLogResult.ILLEGAL, explanation)


def log_error(sess: TBSSession, action: Action, error: Exception) -> None:
    log_event(sess, action, ActionLogResult.ERROR, str(error))
