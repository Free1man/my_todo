from __future__ import annotations
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field
from backend.core.primitives import ISpace, IEntity, IGameState

Color = Literal["white","black"]
PieceType = Literal["pawn","rook","knight","bishop","queen","king"]


class Piece(BaseModel):
    type: PieceType
    color: Color


class Board(BaseModel):
    def in_bounds(self, p) -> bool: return 0 <= p.x < 8 and 0 <= p.y < 8
    def is_walkable(self, p) -> bool: return self.in_bounds(p)


class State(BaseModel):
    board: Dict[str, Piece] = Field(default_factory=dict)  # "e2" -> Piece
    turn: Color = "white"
    castle_K: bool = True
    castle_Q: bool = True
    castle_k: bool = True
    castle_q: bool = True
    en_passant: Optional[str] = None
    halfmove_clock: int = 0
    fullmove_number: int = 1
    status: Literal["ongoing","checkmate","stalemate","draw"] = "ongoing"
    winner: Optional[Color] = None

    @property
    def space(self) -> ISpace: return Board()
    def entities(self) -> Dict[str, IEntity]: return {}
    def to_serializable(self): return self.model_dump()
