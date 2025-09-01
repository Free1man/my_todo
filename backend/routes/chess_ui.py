from __future__ import annotations
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Query, Body

from backend.engine.store import get_session as store_get, save_session as store_set
from backend.core.ruleset_registry import get_ruleset
from backend.rulesets.chess import actions as chess_actions


router = APIRouter(tags=["chess-ui"])


FILES = "abcdefgh"
RANKS = "12345678"


def _state_to_ui_board(st) -> List[List[str]]:
    # 8x8 array of FEN letters, board[0] is rank 8, board[7] is rank 1
    board = [["" for _ in range(8)] for _ in range(8)]
    letter_map = {
        "pawn": "p", "rook": "r", "knight": "n",
        "bishop": "b", "queen": "q", "king": "k",
    }
    for sq, piece in getattr(st, "board", {}).items():
        f = FILES.index(sq[0])
        r = 8 - int(sq[1])
        letter = letter_map.get(getattr(piece, "type", ""), "")
        if not letter:
            continue
        if getattr(piece, "color", "white") == "white":
            letter = letter.upper()
        board[r][f] = letter
    return board


def _state_to_fen(rs, st) -> str:
    try:
        if hasattr(st, "to_fen"):
            return st.to_fen()  # type: ignore
        if hasattr(st, "fen") and callable(getattr(st, "fen")):
            return st.fen()  # type: ignore
        from backend.games.chess.fen import to_fen_from_board
        # convert to board with rank 8 first as outer list
        board_ui = _state_to_ui_board(st)
        board_fen_order = board_ui  # already rank 8..1
        turn = "w" if getattr(st, "turn", "white") == "white" else "b"
        castling = ""
        castling += "K" if getattr(st, "castle_K", False) else ""
        castling += "Q" if getattr(st, "castle_Q", False) else ""
        castling += "k" if getattr(st, "castle_k", False) else ""
        castling += "q" if getattr(st, "castle_q", False) else ""
        castling = castling or "-"
        ep = getattr(st, "en_passant", None) or "-"
        half = int(getattr(st, "halfmove_clock", 0) or 0)
        full = int(getattr(st, "fullmove_number", 1) or 1)
        return to_fen_from_board(board_fen_order, turn, castling, ep, half, full)
    except Exception:
        return "8/8/8/8/8/8/8/8 w - - 0 1"


@router.get("/sessions/{sid}/state")
async def session_state(sid: str) -> Dict[str, Any]:
    s = await store_get(sid)
    if not s:
        raise HTTPException(404, "session not found")
    if s.ruleset != "chess":
        raise HTTPException(400, "session is not chess")
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    board = _state_to_ui_board(st)
    turn = "w" if getattr(st, "turn", "white") == "white" else "b"
    fen = _state_to_fen(rs, st)
    return {"board": board, "turn": turn, "fen": fen}


@router.get("/sessions/{sid}/legal")
async def legal_moves(sid: str, from_: str = Query(alias="from")) -> Dict[str, Any]:
    s = await store_get(sid)
    if not s:
        raise HTTPException(404, "session not found")
    if s.ruleset != "chess":
        raise HTTPException(400, "session is not chess")
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    src = from_.lower()
    if len(src) != 2 or src[0] not in FILES or src[1] not in RANKS:
        return {"to": []}
    # Iterate all squares; keep those that pass evaluation
    out: List[str] = []
    for f in FILES:
        for r in RANKS:
            dst = f + r
            try:
                exp = chess_actions.evaluate(st, {"type": "move", "src": src, "dst": dst})
                if getattr(exp, "ok", False):
                    out.append(dst)
            except Exception:
                pass
    return {"to": out}


@router.post("/sessions/{sid}/move")
async def apply_move(sid: str, payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    s = await store_get(sid)
    if not s:
        raise HTTPException(404, "session not found")
    if s.ruleset != "chess":
        raise HTTPException(400, "session is not chess")
    uci = (payload or {}).get("uci")
    if not uci or len(uci) < 4:
        raise HTTPException(400, "uci required")
    src = uci[0:2].lower()
    dst = uci[2:4].lower()
    promo = None
    if len(uci) > 4:
        m = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}
        promo = m.get(uci[4].lower())
    rs = get_ruleset(s.ruleset)
    st = rs.create(s.state)
    res = rs.apply(st, {"type": "move", "src": src, "dst": dst, "promotion": promo})
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "invalid move"))
    s.state = st.to_serializable()
    await store_set(s)
    return {"ok": True}
