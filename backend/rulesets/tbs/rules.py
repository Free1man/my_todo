from __future__ import annotations
from typing import Dict, Any
from backend.core.primitives import Pos
from .models import State, Unit


def is_adjacent_orthogonal(a: Pos, b: Pos) -> bool:
    return abs(a.x - b.x) + abs(a.y - b.y) == 1


def _occupied(st: State, p: Pos, ignore: str | None = None) -> bool:
    for u in st.units.values():
        if ignore and u.id == ignore: continue
        if u.hp > 0 and u.pos == p: return True
    return False


def can_move_one(st: State, unit: Unit, to: Pos) -> tuple[bool, str | None]:
    if unit.ap <= 0: return False, "No AP left"
    if not st.map.is_walkable(to): return False, "Destination blocked or out of bounds"
    if not is_adjacent_orthogonal(unit.pos, to): return False, "Move one tile orthogonally"
    if _occupied(st, to, ignore=unit.id): return False, "Tile occupied"
    return True, None


def explain_move(st: State, unit: Unit, to: Pos) -> Dict[str, Any]:
    ok, err = can_move_one(st, unit, to)
    return {
        "unit": unit.id,
        "from": unit.pos.model_dump(),
        "to": to.model_dump(),
        "checks": {
            "has_ap": unit.ap > 0,
            "in_bounds": st.map.in_bounds(to),
            "not_obstacle": st.map.is_walkable(to),
            "adjacent_orthogonal": is_adjacent_orthogonal(unit.pos, to),
            "target_occupied": _occupied(st, to, ignore=unit.id),
        },
        "result": ok,
        "reason": None if ok else err,
    }


def in_attack_range(st: State, attacker: Unit, target: Unit) -> bool:
    dist = abs(attacker.pos.x - target.pos.x) + abs(attacker.pos.y - target.pos.y)
    return dist <= attacker.total_range(st.items)


def explain_damage(st: State, attacker: Unit, target: Unit) -> Dict[str, Any]:
    atk = attacker.total_attack(st.items)
    df  = target.total_defense(st.items)
    res = max(1, atk - df)
    return {
        "components": {
            "attacker": {"strength": attacker.strength, "total_attack": atk},
            "defender": {"defense": target.defense, "total_defense": df},
        },
        "formula": "max(1, total_attack - total_defense)",
        "result": res,
    }


def compute_winner(st: State):
    a_alive = any(u.hp > 0 for u in st.units.values() if u.side == "A")
    b_alive = any(u.hp > 0 for u in st.units.values() if u.side == "B")
    if a_alive and not b_alive: return "A"
    if b_alive and not a_alive: return "B"
    return None


def next_unit_index(st: State) -> int:
    n = len(st.turn_order)
    if n == 0: return 0
    for step in range(1, n+1):
        i = (st.active_index + step) % n
        u = st.units.get(st.turn_order[i])
        if u and u.hp > 0: return i
    return st.active_index


def first_alive_index_for_side(st: State, side: str) -> int:
    for i, uid in enumerate(st.turn_order):
        u = st.units.get(uid)
        if u and u.hp > 0 and u.side == side:
            return i
    return st.active_index


def advance_turn(st: State) -> None:
    """Advance turn depending on turn_mode."""
    if st.turn_mode == "unit":
        st.active_index = next_unit_index(st)
        if st.active_index == 0:
            st.turn_number += 1
    else:
        st.active_side = "B" if st.active_side == "A" else "A"
        for u in st.units.values():
            if u.side == st.active_side and u.hp > 0:
                u.ap = u.max_ap
        st.active_index = first_alive_index_for_side(st, st.active_side)
        st.turn_number += 1
