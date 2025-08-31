from __future__ import annotations
from typing import Any, Dict
from backend.core.ruleset_registry import register_ruleset
from backend.core.primitives import Explanation, IGameState
from backend.core import scheduling
from .models import State
from . import actions as acts
from . import factory as fac
from . import rules as rules


class _Ruleset:
    name = "chess"
    default_scheduler = scheduling.SIDE_TO_MOVE

    def create(self, payload: Dict[str, Any] | None = None) -> IGameState:
        return State.model_validate(payload) if payload else fac.quickstart()

    def evaluate(self, state: IGameState, raw_action: Dict[str, Any]) -> Explanation:
        st = State.model_validate(state.to_serializable()); return acts.evaluate(st, raw_action)

    def apply(self, state: IGameState, raw_action: Dict[str, Any]) -> Dict[str, Any]:
        st = State.model_validate(state.to_serializable())
        res = acts.apply(st, raw_action)
        state.__dict__.update(st.__dict__)
        return res

    def summarize(self, state: IGameState) -> Dict[str, Any]:
        st = State.model_validate(state.to_serializable())
        return rules.summarize(st)


ruleset = register_ruleset(_Ruleset())
