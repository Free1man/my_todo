from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import ActionKind, ActionLogResult
from .evaluation import ActionEvaluation
from .mission import Mission

# ----- Actions (discriminated union) -----


class MoveAction(BaseModel):
    kind: ActionKind = ActionKind.MOVE
    unit_id: str
    to: tuple[int, int]


class AttackAction(BaseModel):
    kind: ActionKind = ActionKind.ATTACK
    attacker_id: str
    target_id: str


class UseSkillAction(BaseModel):
    kind: ActionKind = ActionKind.USE_SKILL
    unit_id: str
    skill_id: str
    target_unit_id: str | None = None
    target_tile: tuple[int, int] | None = None
    # Optional: custom AoE shape offsets centered on target tile (0,0 = center)
    # Example: [(-1,-1),(-1,0),...,(1,1)] for a 3x3 square. If None, engine uses skill's default.
    area_offsets: list[tuple[int, int]] | None = None


class EndTurnAction(BaseModel):
    kind: ActionKind = ActionKind.END_TURN


Action = MoveAction | AttackAction | UseSkillAction | EndTurnAction


# ----- API IO -----
class CreateSessionRequest(BaseModel):
    mission: Mission | None = None


class SessionView(BaseModel):
    id: str
    mission: Mission


class EvaluateRequest(BaseModel):
    action: Action


class EvaluateResponse(BaseModel):
    legal: bool
    explanation: str


class ApplyActionRequest(BaseModel):
    action: Action


class ApplyActionResponse(BaseModel):
    applied: bool
    explanation: str
    session: SessionView


# ----- Bulk legal listing -----


class LegalAction(BaseModel):
    action: Action
    explanation: str  # already evaluated and legal
    evaluation: ActionEvaluation | None = None


class LegalActionsResponse(BaseModel):
    actions: list[LegalAction]


# ----- Action Log -----


class ActionLogEntry(BaseModel):
    ts: datetime = Field(default_factory=datetime.now)
    session_id: str
    turn: int
    actor_unit_id: str | None = None
    action: Action
    result: ActionLogResult = ActionLogResult.APPLIED
    message: str | None = None
    attack_eval: dict[str, Any] | None = None


class ActionLogResponse(BaseModel):
    entries: list[ActionLogEntry]
