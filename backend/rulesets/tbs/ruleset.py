from __future__ import annotations
from typing import Any, Dict
from backend.core.ruleset_registry import register_ruleset
from backend.core.primitives import Explanation, IGameState, Pos
from backend.core import scheduling
from backend.core.info_builder import InfoMixin
from .models import State, Unit, Item, Grid
from . import actions as acts
from . import factory as fac


class _Ruleset(InfoMixin):
    name = "tbs"
    default_scheduler = scheduling.UNIT_IGO_UGO

    # tell the mixin what models to expose
    MODEL_SPECS = {"grid": Grid, "unit": Unit, "item": Item, "state": State}

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

    def info(self, state: IGameState | None = None):
        # use session state if provided, else quickstart
        st = State.model_validate(state.to_serializable()) if state else fac.quickstart()
        self.ACTION_SPECS = acts.ACTION_SPECS
        # optional: concrete examples that are valid-now (not just templates)
        def examples(st: State) -> dict:
            ex = {}
            # if there is at least one alive unit, give a move example
            if st.units:
                uid = next(iter(st.units.keys()))
                ex["move"] = {"type":"move","unit_id":uid,"to":{"x":0,"y":0}}
                # naive attack example if two sides exist
                a = next((u for u in st.units.values() if u.side=="A"), None)
                b = next((u for u in st.units.values() if u.side=="B"), None)
                if a and b:
                    ex["attack"] = {"type":"attack","attacker_id":a.id,"target_id":b.id}
            ex["end_turn"] = {"type":"end_turn"}
            return ex
        self.build_examples = examples  # plug into mixin
        return self.default_info(st)


ruleset = register_ruleset(_Ruleset())
