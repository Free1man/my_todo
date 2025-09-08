from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from backend.models.api import Action
    from backend.models.enums import ActionLogResult


@dataclass
class ActionEvent:
    session_id: str
    turn: int
    actor_unit_id: str | None
    action: Action
    result: ActionLogResult
    message: str | None = None
    attack_eval: dict | None = None


T = TypeVar("T")


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[type[Any], list[object]] = {}

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        lst = self._subs.setdefault(event_type, [])
        lst.append(cast("object", handler))

    def emit(self, event: Any) -> None:
        et = type(event)
        for h in self._subs.get(et, []):
            # Let exceptions propagate; callers decide how to handle them
            cast("Callable[[Any], None]", h)(event)


# Global bus instance
event_bus = EventBus()
