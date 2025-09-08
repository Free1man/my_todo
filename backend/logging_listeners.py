from __future__ import annotations

from . import storage
from .events import ActionEvent, event_bus
from .models.api import ActionLogEntry


def _on_action_event(ev: ActionEvent) -> None:
    # Convert event to ActionLogEntry JSON for persistence
    entry = ActionLogEntry(
        session_id=ev.session_id,
        turn=ev.turn,
        actor_unit_id=ev.actor_unit_id,
        action=ev.action,
        result=ev.result,
        message=ev.message,
        attack_eval=ev.attack_eval,
    )
    storage.logs.append(ev.session_id, entry.model_dump_json())


def register_listeners() -> None:
    event_bus.subscribe(ActionEvent, _on_action_event)
