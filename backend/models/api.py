from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Tuple, Literal

from .common import Mission

# ----- Actions (discriminated union) -----

class MoveAction(BaseModel):
    kind: Literal["MOVE"] = "MOVE"
    unit_id: str
    to: Tuple[int, int]

class AttackAction(BaseModel):
    kind: Literal["ATTACK"] = "ATTACK"
    attacker_id: str
    target_id: str

class UseSkillAction(BaseModel):
    kind: Literal["USE_SKILL"] = "USE_SKILL"
    unit_id: str
    skill_id: str
    target_unit_id: Optional[str] = None
    target_tile: Optional[Tuple[int, int]] = None

class EndTurnAction(BaseModel):
    kind: Literal["END_TURN"] = "END_TURN"

Action = MoveAction | AttackAction | UseSkillAction | EndTurnAction

# ----- API IO -----
class CreateSessionRequest(BaseModel):
    mission: Optional[Mission] = None

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

class LegalActionsResponse(BaseModel):
    actions: List[LegalAction]
