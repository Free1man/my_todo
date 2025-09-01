import os
import re
from typing import Optional, Tuple

import httpx

UA = os.getenv("AI_USER_AGENT", "AbstractTactics/0.1 (+contact: you@example.com)")

_piece_re = re.compile(r"^[prnbqkPRNBQK]$")


def _count_pieces_in_fen(fen: str) -> int:
    board = fen.split()[0]
    n = 0
    for ch in board:
        if _piece_re.match(ch):
            n += 1
        # digits and / are squares or rank sep
    return n


async def lichess_tablebase_best_uci(fen: str) -> Optional[str]:
    # Perfect play for <= 7 men
    async with httpx.AsyncClient(timeout=6, headers={"User-Agent": UA}) as client:
        r = await client.get("http://tablebase.lichess.ovh/standard", params={"fen": fen})
        if r.status_code != 200:
            return None
        j = r.json()
        moves = j.get("moves") or []
        return moves[0]["uci"] if moves else None


async def lichess_cloud_eval_best_uci(fen: str, multipv: int = 1) -> Optional[str]:
    # Cached Stockfish analysis from Lichess
    async with httpx.AsyncClient(timeout=6, headers={"Accept": "application/json", "User-Agent": UA}) as client:
        r = await client.get(
            "https://lichess.org/api/cloud-eval", params={"fen": fen, "multiPv": multipv}
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        j = r.json()
        pvs = j.get("pvs") or []
        if not pvs:
            return None
        # pvs[0]["moves"] is space-separated UCI line, first token is the best move.
        return (pvs[0].get("moves") or "").split(" ")[0] or None


async def chessdb_best_uci(fen: str) -> Optional[str]:
    # Free community engine/book
    async with httpx.AsyncClient(timeout=6, headers={"User-Agent": UA}) as client:
        r = await client.get(
            "http://www.chessdb.cn/cdb.php", params={"action": "querybest", "board": fen}
        )
        if r.status_code != 200:
            return None
        # returns like: "move:e7e5 ponder:..."; we just need the move
        txt = (r.text or "").strip()
        if "move:" in txt:
            return txt.split("move:")[1].split()[0]
        return None


async def best_move_uci(fen: str) -> Tuple[Optional[str], str]:
    """
    Returns (uci, source).
    Strategy: TB (<=7 men) -> Lichess Cloud -> ChessDB.
    """
    try:
        if _count_pieces_in_fen(fen) <= 7:
            m = await lichess_tablebase_best_uci(fen)
            if m:
                return m, "lichess-tablebase"
        m = await lichess_cloud_eval_best_uci(fen)
        if m:
            return m, "lichess-cloud-eval"
        m = await chessdb_best_uci(fen)
        if m:
            return m, "chessdb"
        return None, "none"
    except httpx.HTTPError:
        return None, "error"
