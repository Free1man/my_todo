# tests/integration/test_chess_en_passant_line.py
import requests
import pytest

def _new_session(base_url: str) -> str:
    r = requests.post(f"{base_url}/sessions", json={"ruleset": "chess"}, timeout=5)
    r.raise_for_status()
    return r.json()["id"]

def _eval_move(base_url: str, sid: str, src: str, dst: str) -> dict:
    r = requests.post(
        f"{base_url}/sessions/{sid}/evaluate",
        json={"type": "move", "src": src, "dst": dst},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()

def _move(base_url: str, sid: str, src: str, dst: str) -> dict:
    r = requests.post(
        f"{base_url}/sessions/{sid}/action",
        json={"type": "move", "src": src, "dst": dst},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()

def test_en_passant_works_immediately(base_url: str):
    # Line: 1.e4 e6 2.e5 d5 3.exd6 e.p.  (coordinates)
    sid = _new_session(base_url)
    for src, dst in [("e2","e4"), ("e7","e6"), ("e4","e5"), ("d7","d5")]:
        assert _eval_move(base_url, sid, src, dst)["ok"]
        _move(base_url, sid, src, dst)

    # EP capture must be legal now (White pawn from e5 to d6)
    assert _eval_move(base_url, sid, "e5", "d6")["ok"]
    last = _move(base_url, sid, "e5", "d6")
    board = last["state"]["board"]
    # Pawn landed on d6, black pawn from d5 is gone
    assert board.get("d6", {}).get("type") == "pawn" and board["d6"]["color"] == "white"
    assert "d5" not in board or board["d5"] is None

def test_en_passant_not_allowed_late(base_url: str):
    # Same start but White "waits" a move, losing the EP right
    sid = _new_session(base_url)
    for src, dst in [("e2","e4"), ("e7","e6"), ("e4","e5"), ("d7","d5"), ("g1","f3"), ("b8","c6")]:
        assert _eval_move(base_url, sid, src, dst)["ok"]
        _move(base_url, sid, src, dst)

    # En passant should now be rejected
    ex = _eval_move(base_url, sid, "e5", "d6")
    assert not ex.get("ok"), f"EP should be illegal after an intervening move, got: {ex}"
    with pytest.raises(Exception):
        _move(base_url, sid, "e5", "d6")
