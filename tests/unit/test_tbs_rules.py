from backend.rulesets.tbs.factory import quickstart
from backend.rulesets.tbs.models import State
from backend.rulesets.tbs.rules import can_move_one, in_attack_range, explain_damage, compute_winner
from backend.core.primitives import Pos


def test_move_one_ok_and_ap():
    st: State = quickstart()
    uid = st.turn_order[0]
    u = st.units[uid]
    ok, err = can_move_one(st, u, Pos(x=u.pos.x, y=u.pos.y+1))
    assert ok and err is None


def test_move_blocked_or_occupied():
    st: State = quickstart()
    # place an obstacle in front of unit0
    uid = st.turn_order[0]; u = st.units[uid]
    st.map.obstacles.append(Pos(x=u.pos.x, y=u.pos.y+1))
    ok, err = can_move_one(st, u, Pos(x=u.pos.x, y=u.pos.y+1))
    assert not ok and "blocked" in err


def test_attack_range_and_damage_explain():
    st: State = quickstart()
    # Bring attacker and target adjacent
    a = st.units[st.turn_order[0]]
    b = st.units[st.turn_order[-1]]
    b.pos = Pos(x=a.pos.x+1, y=a.pos.y)
    assert in_attack_range(st, a, b)
    info = explain_damage(st, a, b)
    assert info["result"] >= 1
    assert "components" in info and "formula" in info


def test_victory_when_side_eliminated():
    st: State = quickstart()
    # kill all B units
    for u in st.units.values():
        if u.side == "B":
            u.hp = 0
    w = compute_winner(st)
    assert w == "A"
