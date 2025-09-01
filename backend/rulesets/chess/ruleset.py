from __future__ import annotations
from typing import Any, Dict
from backend.core.ruleset_registry import register_ruleset
from backend.core.primitives import Explanation, IGameState
from backend.core import scheduling
from backend.core.info_builder import InfoMixin
from .models import State, Piece, Board
from . import actions as acts
from . import factory as fac
from . import rules as rules


class _Ruleset(InfoMixin):
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

    def info(self, state: IGameState | None = None):
        self.ACTION_SPECS = acts.ACTION_SPECS
        # chess examples are trivial
        self.build_examples = lambda st: {
            "move": {"type":"move","src":"e2","dst":"e4"}
        }
        # no extra model_specs needed unless you want to expose FEN etc.
        return self.default_info(state)


ruleset = register_ruleset(_Ruleset())
