from __future__ import annotations
from typing import Any, Dict
from backend.core.ruleset_registry import register_ruleset
from backend.core.primitives import Explanation, IGameState
from backend.core import scheduling
from .models import State
from . import actions as acts
from . import factory as fac


class _Ruleset:
    name = "tbs"
    default_scheduler = scheduling.UNIT_IGO_UGO

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
        active = st.turn_order[st.active_index] if st.turn_order else None
        return {"turn_number": st.turn_number, "active_unit_id": active, "status": st.status, "winner": st.winner}


ruleset = register_ruleset(_Ruleset())
