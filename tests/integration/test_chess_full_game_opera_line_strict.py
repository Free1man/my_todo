# tests/test_chess_full_game_opera_line_strict.py
import requests

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

def _play_line(base_url: str, sid: str, line: list[tuple[str, str]]) -> dict:
    sess = None
    for src, dst in line:
        ex = _eval_move(base_url, sid, src, dst)
        assert ex.get("ok"), f"Illegal move according to /evaluate: {src}->{dst}, got: {ex}"
        sess = _move(base_url, sid, src, dst)
    return sess

def _norm_piece(p: dict) -> dict:
    return {"type": p.get("type"), "color": p.get("color")}

def _normalize_board(board: dict[str, dict]) -> dict[str, dict]:
    return {sq: _norm_piece(p) for sq, p in board.items() if p}

# Morphy's Opera Game as coordinate moves (ends with 17.Rd8#)
OPERA_COORDS: list[tuple[str, str]] = [
    ("e2","e4"), ("e7","e5"),
    ("g1","f3"), ("d7","d6"),
    ("d2","d4"), ("c8","g4"),
    ("d4","e5"), ("g4","f3"),
    ("d1","f3"), ("d6","e5"),
    ("f1","c4"), ("g8","f6"),
    ("f3","b3"), ("d8","e7"),
    ("b1","c3"), ("c7","c6"),
    ("c1","g5"), ("b7","b5"),
    ("c3","b5"), ("c6","b5"),
    ("c4","b5"), ("b8","d7"),
    ("e1","c1"), ("a8","d8"),
    ("d1","d7"), ("d8","d7"),
    ("h1","d1"), ("e7","e6"),
    ("b5","d7"), ("f6","d7"),
    ("b3","b8"), ("d7","b8"),
    ("d1","d8"),
]

# Expected FINAL board after 17.Rd8# (strict, from Wikipedia's final diagram)
EXPECTED_FINAL = {
    # White
    "c1": {"type": "king",  "color": "white"},
    "d8": {"type": "rook",  "color": "white"},
    "g5": {"type": "bishop","color": "white"},
    "a2": {"type": "pawn",  "color": "white"},
    "b2": {"type": "pawn",  "color": "white"},
    "c2": {"type": "pawn",  "color": "white"},
    "e4": {"type": "pawn",  "color": "white"},
    "f2": {"type": "pawn",  "color": "white"},
    "g2": {"type": "pawn",  "color": "white"},
    "h2": {"type": "pawn",  "color": "white"},
    # Black
    "e8": {"type": "king",  "color": "black"},
    "e6": {"type": "queen", "color": "black"},
    "f8": {"type": "bishop","color": "black"},
    "b8": {"type": "knight","color": "black"},
    "h8": {"type": "rook",  "color": "black"},
    "a7": {"type": "pawn",  "color": "black"},
    "e5": {"type": "pawn",  "color": "black"},
    "f7": {"type": "pawn",  "color": "black"},
    "g7": {"type": "pawn",  "color": "black"},
    "h7": {"type": "pawn",  "color": "black"},
}

def test_chess_full_game_opera_final_board_exact(base_url: str):
    sid = _new_session(base_url)
    last = _play_line(base_url, sid, OPERA_COORDS)

    # Normalize your engine's board to {square: {type,color}}
    board = _normalize_board(last["state"]["board"])

    # 1) same set of squares (no missing, no extra)
    expected_squares = set(EXPECTED_FINAL.keys())
    actual_squares = set(board.keys())
    extra = sorted(actual_squares - expected_squares)
    missing = sorted(expected_squares - actual_squares)
    assert not extra and not missing, (
        f"Final board squares mismatch.\n"
        f"Extra squares (should NOT exist): {extra}\n"
        f"Missing squares (should exist): {missing}\n"
    )

    # 2) same piece on each square
    wrong = []
    for sq in sorted(expected_squares):
        if board.get(sq) != EXPECTED_FINAL[sq]:
            wrong.append((sq, board.get(sq), EXPECTED_FINAL[sq]))
    assert not wrong, (
        "Incorrect pieces on squares:\n" +
        "\n".join(f"  {sq}: got {got}, expected {exp}" for sq, got, exp in wrong)
    )

    # 3) Optional sanity: piece counts by color/type
    def count(color: str, typ: str) -> int:
        return sum(1 for p in board.values() if p["color"] == color and p["type"] == typ)

    assert count("white","king")==1 and count("black","king")==1
    assert count("white","rook")==1 and count("black","rook")==1
    assert count("white","bishop")==1 and count("black","bishop")==1
    assert count("white","knight")==0 and count("black","knight")==1
    assert count("white","queen")==0 and count("black","queen")==1
    assert count("white","pawn")==7 and count("black","pawn")==5
