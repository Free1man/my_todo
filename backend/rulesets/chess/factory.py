from __future__ import annotations
from typing import Optional, Dict
from .models import State, Piece


def quickstart(board: Optional[Dict[str, Piece]] = None) -> State:
    """Create an initial chess state; pass a custom board mapping to override."""
    if board is None:
        # Import lazily to avoid cycles
        from .rules import initial_board
        board = initial_board()
    return State(board=board)
