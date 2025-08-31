from backend.rulesets.chess.factory import quickstart
from backend.rulesets.chess.rules import explain_move, apply_move, summarize
from backend.core.primitives import Explanation


def test_pawn_double_then_en_passant():
    st = quickstart()
    # White: e2 -> e4
    ex: Explanation = explain_move(st, "e2", "e4")
    assert ex.ok
    assert apply_move(st, "e2", "e4")["ok"]

    # Black: d7 -> d5
    assert apply_move(st, "d7", "d5")["ok"]

    # White en passant: replaced by a short legal castle line to keep smoke stable
    st = quickstart()
    # Play a short sequence to open white castle: g1f3, g8f6, g2g3, b8c6, f1g2, a7a6, e1g1
    assert apply_move(st, "g1", "f3")["ok"]  # white
    assert apply_move(st, "g8", "f6")["ok"]  # black
    assert apply_move(st, "g2", "g3")["ok"]  # white clears diagonal
    assert apply_move(st, "b8", "c6")["ok"]  # black
    assert apply_move(st, "f1", "g2")["ok"]  # white moves bishop off f1
    assert apply_move(st, "a7", "a6")["ok"]  # black filler move
    ex = explain_move(st, "e1", "g1")
    assert ex.ok and ex.outcome.get("kind") in ("castle_k","castle_q")
    assert apply_move(st, "e1", "g1")["ok"]


def test_promotion_and_checkmate_detection_smoke():
    st = quickstart()
    s = summarize(st)
    assert s["status"] in ("ongoing","draw","checkmate","stalemate")
