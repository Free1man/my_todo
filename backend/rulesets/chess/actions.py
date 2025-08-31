from __future__ import annotations
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel
from backend.core.primitives import Explanation
from .models import State, PieceType
from .rules import explain_move, apply_move


class MovePayload(BaseModel):
    type: Literal["move"] = "move"
    src: str
    dst: str
    promotion: Optional[PieceType] = None


def parse(raw: Dict[str, Any]) -> MovePayload:
    if raw.get("type") != "move":
        raise ValueError("Unknown chess action")
    return MovePayload.model_validate(raw)


def evaluate(st: State, raw: Dict[str, Any]) -> Explanation:
    p = parse(raw); return explain_move(st, p.src, p.dst, p.promotion)


def apply(st: State, raw: Dict[str, Any]) -> Dict[str, Any]:
    p = parse(raw); return apply_move(st, p.src, p.dst, p.promotion)
