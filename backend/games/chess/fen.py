from typing import List, Optional


def to_fen_from_board(
    board: List[List[Optional[str]]],  # ranks 8..1 as outer list; files a..h inner; pieces like "p","N", None
    turn: str,  # "w" | "b"
    castling: str,  # e.g. "KQkq" or "-"
    ep: Optional[str],  # like "e3" or None/"-"
    halfmove_clock: int,
    fullmove_number: int,
) -> str:
    ranks = []
    for rank in board:  # expects rank 8 first
        empty = 0
        parts = []
        for sq in rank:
            if not sq:
                empty += 1
            else:
                if empty:
                    parts.append(str(empty)); empty = 0
                parts.append(sq)
        if empty:
            parts.append(str(empty))
        ranks.append("".join(parts))
    board_fen = "/".join(ranks)
    ep_part = ep if ep and ep != "-" else "-"
    return f"{board_fen} {turn} {castling or '-'} {ep_part} {halfmove_clock} {fullmove_number}"
