from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ...models.api import Action
    from ...models.mission import Mission
    from ...models.session import TBSSession


class ActionHandler(Protocol):
    action_type: type

    def evaluate(self, mission: Mission, action: Action) -> tuple[bool, str]: ...

    def apply(self, sess: TBSSession, action: Action) -> TBSSession: ...


Registry = dict[type, ActionHandler]
