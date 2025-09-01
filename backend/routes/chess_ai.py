from __future__ import annotations
from typing import Optional, Tuple, Any, Dict

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from backend.engine.store import get_session as store_get, save_session as store_set
from backend.core.ruleset_registry import get_ruleset
from backend.ai.chess_providers import best_move_uci

router = APIRouter(prefix="/chess/ai", tags=["chess-ai"])


class NextMoveIn(BaseModel):
    fen: Optional[str] = None
    session_id: Optional[str] = None
    apply: bool = False


class NextMoveOut(BaseModel):
    ok: bool
    engine: str
    fen: str
    uci: str


def _state_to_fen(rs, st) -> str:
    # Try ruleset-specific FEN exporters if present; otherwise build minimal FEN.
    # chess rules keep enough info to emit a complete FEN with defaults if missing.
    # Minimal fallback: board-only + side to move.
    if hasattr(st, "to_fen"):
        return st.to_fen()  # type: ignore[attr-defined]
    if hasattr(st, "fen") and callable(getattr(st, "fen")):
        return st.fen()  # type: ignore[attr-defined]
    # fallback builder from board model
    try:
        from backend.games.chess.fen import to_fen_from_board  # type: ignore
        board8 = [[None for _ in range(8)] for _ in range(8)]
        files = "abcdefgh"; ranks = "12345678"
        letter_map = {
            "pawn": "p", "rook": "r", "knight": "n",
            "bishop": "b", "queen": "q", "king": "k",
        }
        for sq, piece in getattr(st, "board", {}).items():
            x = files.index(sq[0]); y = ranks.index(sq[1])
            letter = letter_map.get(getattr(piece, "type", ""), "")
            if not letter:
                continue
            if getattr(piece, "color", "white") == "white":
                letter = letter.upper()
            board8[y][x] = letter
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
        return to_fen_from_board(board8[::-1], turn, castling, ep, half, full)
    except Exception:
        # last resort
        return "8/8/8/8/8/8/8/8 w - - 0 1"


@router.post("/next", response_model=NextMoveOut)
async def next_move(payload: NextMoveIn = Body(...)) -> NextMoveOut:
    # Resolve FEN
    if payload.fen:
        fen = payload.fen
    elif payload.session_id:
        s = await store_get(payload.session_id)
        if not s:
            raise HTTPException(404, "session not found")
        if s.ruleset != "chess":
            raise HTTPException(400, "session is not chess")
        rs = get_ruleset(s.ruleset)
        st = rs.create(s.state)
        fen = _state_to_fen(rs, st)
    else:
        raise HTTPException(400, "provide fen or session_id")

    # Ask engines
    uci, source = await best_move_uci(fen)
    if not uci:
        raise HTTPException(502, "no engine move available")

    # Apply into session via normal flow (optional)
    if payload.apply and payload.session_id:
        s = await store_get(payload.session_id)
        if not s:
            raise HTTPException(404, "session not found")
        if s.ruleset != "chess":
            raise HTTPException(400, "session is not chess")
        rs = get_ruleset(s.ruleset)
        st = rs.create(s.state)
        # UCI like e2e4[,q]; translate to our action schema
        src, dst, promo = uci[:2] + uci[2:4], uci[2:4], None
        # correct splitting: e2e4 or e7e8q
        src = uci[0:2]
        dst = uci[2:4]
        if len(uci) > 4:
            m = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}
            promo = m.get(uci[4].lower())
        res = rs.apply(st, {"type": "move", "src": src, "dst": dst, "promotion": promo})
        if not res.get("ok"):
            raise HTTPException(400, f"failed to apply move: {res.get('error')}")
        s.state = st.to_serializable()
        await store_set(s)

    return NextMoveOut(ok=True, engine=source, fen=fen, uci=uci)
