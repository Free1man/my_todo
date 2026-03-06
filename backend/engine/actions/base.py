from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ...models.api import Action
    from ..runtime import RuntimeMission, RuntimeSession


class ActionHandler(Protocol):
    action_type: type

    def evaluate(self, mission: RuntimeMission, action: Action) -> tuple[bool, str]: ...

    def apply(self, sess: RuntimeSession, action: Action) -> RuntimeSession: ...


Registry = dict[type, ActionHandler]
