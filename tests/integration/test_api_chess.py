import requests


def _move(base_url: str, sid: str, src: str, dst: str):
    r = requests.post(
        f"{base_url}/sessions/{sid}/action",
        json={"type": "move", "src": src, "dst": dst},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def test_chess_castle_line(base_url: str):
    # Create a Chess session
    r = requests.post(f"{base_url}/sessions", json={"ruleset": "chess"}, timeout=5)
    r.raise_for_status()
    sess = r.json()
    sid = sess["id"]

    # Short opening to enable white castle
    _move(base_url, sid, "g1", "f3")
    _move(base_url, sid, "g8", "f6")
    _move(base_url, sid, "g2", "g3")
    _move(base_url, sid, "b8", "c6")
    _move(base_url, sid, "f1", "g2")
    _move(base_url, sid, "a7", "a6")

    # Evaluate castling
    r = requests.post(
        f"{base_url}/sessions/{sid}/evaluate",
        json={"type": "move", "src": "e1", "dst": "g1"},
        timeout=5,
    )
    r.raise_for_status()
    ex = r.json()
    assert ex["ok"]

    # Apply castling
    sess = _move(base_url, sid, "e1", "g1")
    board = sess["state"]["board"]
    # King should now be on g1
    assert board.get("g1", {}).get("type") == "king"
    assert board.get("g1", {}).get("color") == "white"
    # e1 should no longer contain the white king
    e1 = board.get("e1")
    assert not (e1 and e1.get("type") == "king" and e1.get("color") == "white")
