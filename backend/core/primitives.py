from __future__ import annotations
from typing import Protocol, Dict, Any, List
from pydantic import BaseModel, Field


class Pos(BaseModel):
    """Grid/board coordinate (0-based)."""
    x: int
    y: int


class IEntity(Protocol):
    id: str
    side: str  # e.g., "A"/"B" or "white"/"black"


class ISpace(Protocol):
    def in_bounds(self, p: Pos) -> bool: ...
    def is_walkable(self, p: Pos) -> bool: ...


class IGameState(Protocol):
    """Typed state object a ruleset returns from create(); must round-trip via to_serializable()."""
    space: ISpace
    def entities(self) -> Dict[str, IEntity]: ...
    def to_serializable(self) -> Dict[str, Any]: ...


class Explanation(BaseModel):
    """Detailed reasoning for the UI (why legal, intermediate numbers, outcomes)."""
    ok: bool
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    outcome: Dict[str, Any] = Field(default_factory=dict)
