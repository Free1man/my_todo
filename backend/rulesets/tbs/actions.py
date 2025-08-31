from __future__ import annotations
from typing import Any, Dict, Literal
from pydantic import BaseModel
from backend.core.primitives import Explanation, Pos
from .models import State
from .rules import can_move_one, explain_move, in_attack_range, explain_damage, compute_winner, advance_turn


class MovePayload(BaseModel):
    type: Literal["move"] = "move"
    unit_id: str
    to: Pos


class AttackPayload(BaseModel):
    type: Literal["attack"] = "attack"
    attacker_id: str
    target_id: str


class EndTurnPayload(BaseModel):
    type: Literal["end_turn"] = "end_turn"


_HANDLERS: Dict[str, Any] = {}


def _register(t: str):
    def deco(cls):
        _HANDLERS[t] = cls()
        return cls
    return deco


def parse(raw: Dict[str, Any]):
    t = raw.get("type")
    if t == "move": return MovePayload.model_validate(raw)
    if t == "attack": return AttackPayload.model_validate(raw)
    if t == "end_turn": return EndTurnPayload.model_validate(raw)
    raise ValueError(f"Unknown action type: {t}")


@_register("move")
class MoveHandler:
    def evaluate(self, st: State, p: MovePayload) -> Explanation:
        u = st.units.get(p.unit_id)
        if not u or u.hp <= 0:
            return Explanation(ok=False, steps=[{"check":"unit_alive","ok":False}])
        info = explain_move(st, u, p.to)
        return Explanation(ok=bool(info["result"]), steps=[{"check":"move_rules","ok":bool(info["result"]), "info":info}],
                           outcome={"ap_after": max(0, u.ap-1) if info["result"] else u.ap})

    def apply(self, st: State, p: MovePayload) -> Dict[str, Any]:
        u = st.units.get(p.unit_id)
        if not u or u.hp <= 0: return {"ok": False, "error": "Unit not alive"}
        ok, err = can_move_one(st, u, p.to)
        if not ok: return {"ok": False, "error": err}
        u.pos = p.to
        u.ap = max(0, u.ap - 1)
        return {"ok": True}


@_register("attack")
class AttackHandler:
    def evaluate(self, st: State, p: AttackPayload) -> Explanation:
        a = st.units.get(p.attacker_id); t = st.units.get(p.target_id)
        if not a or a.hp <= 0 or not t or t.hp <= 0:
            return Explanation(ok=False, steps=[{"check":"alive","ok":False}])
        if not in_attack_range(st, a, t):
            return Explanation(ok=False, steps=[{"check":"in_range","ok":False}])
        dmg = explain_damage(st, a, t)
        return Explanation(ok=True, steps=[{"check":"in_range","ok":True}],
                           outcome={"damage": dmg, "ap_after": max(0, a.ap-1)})

    def apply(self, st: State, p: AttackPayload) -> Dict[str, Any]:
        a = st.units.get(p.attacker_id); t = st.units.get(p.target_id)
        if not a or a.hp <= 0 or not t or t.hp <= 0: return {"ok":False,"error":"Attacker/target not alive"}
        if not in_attack_range(st, a, t): return {"ok":False,"error":"Out of range"}
        dmg = max(1, a.total_attack(st.items) - t.total_defense(st.items))
        t.hp = max(0, t.hp - dmg)
        a.ap = max(0, a.ap - 1)
        w = compute_winner(st)
        if w: st.status = "finished"; st.winner = w
        return {"ok": True, "damage": dmg}


@_register("end_turn")
class EndTurnHandler:
    def evaluate(self, st: State, p: EndTurnPayload) -> Explanation:
        uid = st.turn_order[st.active_index] if st.turn_order else None
        u = st.units.get(uid) if uid else None
        return Explanation(ok=True, steps=[{"check":"noop","ok":True}],
                           outcome={"active_unit": uid, "ap_will_reset_to": u.max_ap if u else None})

    def apply(self, st: State, p: EndTurnPayload) -> Dict[str, Any]:
        if st.turn_mode == "unit":
            uid = st.turn_order[st.active_index] if st.turn_order else None
            u = st.units.get(uid) if uid else None
            if u and u.hp > 0: u.ap = u.max_ap
        advance_turn(st)
        return {"ok": True}


def evaluate(st: State, raw: Dict[str, Any]) -> Explanation:
    p = parse(raw); return _HANDLERS[p.type].evaluate(st, p)


def apply(st: State, raw: Dict[str, Any]) -> Dict[str, Any]:
    p = parse(raw); return _HANDLERS[p.type].apply(st, p)
