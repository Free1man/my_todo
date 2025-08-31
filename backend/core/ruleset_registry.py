from __future__ import annotations
from typing import Dict, Any, Protocol
from backend.core.primitives import IGameState, Explanation


class IRuleset(Protocol):
    name: str
    default_scheduler: str
    def create(self, payload: Dict[str, Any] | None = None) -> IGameState: ...
    def evaluate(self, state: IGameState, raw_action: Dict[str, Any]) -> Explanation: ...
    def apply(self, state: IGameState, raw_action: Dict[str, Any]) -> Dict[str, Any]: ...
    def summarize(self, state: IGameState) -> Dict[str, Any]: ...


_REG: Dict[str, IRuleset] = {}


def register_ruleset(r: IRuleset):
    _REG[r.name] = r
    return r


def get_ruleset(name: str) -> IRuleset:
    if name not in _REG:
        raise KeyError(f"Unknown ruleset: {name}")
    return _REG[name]


def list_rulesets() -> Dict[str, str]:
    return {k: v.default_scheduler for k, v in _REG.items()}
