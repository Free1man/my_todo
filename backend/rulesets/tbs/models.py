from __future__ import annotations
from typing import Dict, List, Literal
from pydantic import BaseModel, Field
from backend.core.primitives import Pos, ISpace, IEntity, IGameState


class Grid(BaseModel):
    width: int
    height: int
    obstacles: List[Pos] = Field(default_factory=list)
    def in_bounds(self, p: Pos) -> bool: return 0 <= p.x < self.width and 0 <= p.y < self.height
    def is_walkable(self, p: Pos) -> bool: return self.in_bounds(p) and (p not in self.obstacles)


class Item(BaseModel):
    id: str
    name: str
    attack_bonus: int = 0
    defense_bonus: int = 0
    range_bonus: int = 0


class Unit(BaseModel):
    id: str
    side: str
    name: str
    strength: int = 3
    defense: int = 1
    max_hp: int = 10
    hp: int = 10
    max_ap: int = 2
    ap: int = 2
    pos: Pos
    item_ids: List[str] = Field(default_factory=list)

    def total_attack(self, items: Dict[str, Item]) -> int:
        return self.strength + sum(items[i].attack_bonus for i in self.item_ids if i in items)
    def total_defense(self, items: Dict[str, Item]) -> int:
        return self.defense + sum(items[i].defense_bonus for i in self.item_ids if i in items)
    def total_range(self, items: Dict[str, Item]) -> int:
        return 1 + sum(items[i].range_bonus for i in self.item_ids if i in items)


class State(BaseModel):
    map: Grid
    items: Dict[str, Item] = Field(default_factory=dict)
    units: Dict[str, Unit] = Field(default_factory=dict)
    turn_order: List[str] = Field(default_factory=list)  # unit ids
    active_index: int = 0
    turn_number: int = 1
    status: str = "ongoing"
    winner: str | None = None
    # scheduler knobs (simple; can be extended later)
    turn_mode: Literal["unit","side"] = "unit"
    active_side: str = "A"

    @property
    def space(self) -> ISpace: return self.map
    def entities(self) -> Dict[str, IEntity]: return {uid: u for uid, u in self.units.items()}
    def to_serializable(self) -> Dict[str, object]: return self.model_dump()
