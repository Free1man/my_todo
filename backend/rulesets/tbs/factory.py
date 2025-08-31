from __future__ import annotations
from uuid import uuid4
from backend.core.primitives import Pos
from .models import State, Grid, Item, Unit


def quickstart() -> State:
    m = Grid(width=6, height=6, obstacles=[Pos(x=2,y=2), Pos(x=3,y=2)])
    sword = Item(id=uuid4().hex, name="Sword", attack_bonus=2)
    shield = Item(id=uuid4().hex, name="Shield", defense_bonus=1)
    bow = Item(id=uuid4().hex, name="Bow", range_bonus=1)

    a = Unit(id=uuid4().hex, side="A", name="Alice", pos=Pos(x=0,y=0), item_ids=[sword.id])
    b = Unit(id=uuid4().hex, side="B", name="Bob",   pos=Pos(x=5,y=5), item_ids=[shield.id])
    c = Unit(id=uuid4().hex, side="A", name="Cara",  pos=Pos(x=1,y=1), item_ids=[bow.id], strength=2, defense=1, max_hp=8, hp=8)

    return State(map=m,
                 items={i.id: i for i in [sword, shield, bow]},
                 units={u.id: u for u in [a,b,c]},
                 turn_order=[a.id, c.id, b.id])
