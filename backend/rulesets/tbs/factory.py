from __future__ import annotations
from uuid import uuid4
from typing import Iterable, Optional, List, Dict
from backend.core.primitives import Pos
from .models import State, Grid, Item, Unit


def quickstart(
    width: int = 6,
    height: int = 6,
    obstacles: Optional[Iterable[Pos]] = None,
    items: Optional[Iterable[Item]] = None,
    units: Optional[Iterable[Unit]] = None,
    turn_order: Optional[List[str]] = None,
) -> State:
    """Create a small demo state; accepts overrides for easy experiments."""
    m = Grid(width=width, height=height, obstacles=list(obstacles or [Pos(x=2, y=2), Pos(x=3, y=2)]))

    if items is None:
        sword = Item(id=uuid4().hex, name="Sword", attack_bonus=2)
        shield = Item(id=uuid4().hex, name="Shield", defense_bonus=1)
        bow = Item(id=uuid4().hex, name="Bow", range_bonus=1)
        items = [sword, shield, bow]

    if units is None:
        sword, shield, bow = list(items)  # type: ignore
        a = Unit(id=uuid4().hex, side="A", name="Alice", pos=Pos(x=0, y=0), item_ids=[sword.id])
        b = Unit(id=uuid4().hex, side="B", name="Bob",   pos=Pos(x=5, y=5), item_ids=[shield.id])
        c = Unit(id=uuid4().hex, side="A", name="Cara",  pos=Pos(x=1, y=1), item_ids=[bow.id], strength=2, defense=1, max_hp=8, hp=8)
        units = [a, b, c]

    items_map: Dict[str, Item] = {i.id: i for i in items}
    units_map: Dict[str, Unit] = {u.id: u for u in units}
    to = turn_order or [u.id for u in units]  # default: listed order
    return State(map=m, items=items_map, units=units_map, turn_order=to)
