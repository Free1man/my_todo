from pydantic import BaseModel, Field

from .enums import GoalKind, MissionStatus, Side
from .map import MapGrid
from .modifiers import StatModifier
from .units import Unit


class MissionGoal(BaseModel):
    kind: GoalKind
    survive_turns: int | None = None


class MissionEvent(BaseModel):
    id: str
    text: str


class Mission(BaseModel):
    id: str
    name: str
    map: MapGrid
    units: dict[str, Unit]
    side_to_move: Side = Side.PLAYER
    turn: int = 1
    max_turns: int | None = None
    goals: list[MissionGoal] = Field(default_factory=list)
    pre_events: list[MissionEvent] = Field(default_factory=list)
    post_events: list[MissionEvent] = Field(default_factory=list)
    global_mods: list[StatModifier] = Field(default_factory=list)
    initiative_order: list[str] = Field(default_factory=list)
    current_unit_id: str | None = None
    status: MissionStatus = MissionStatus.IN_PROGRESS
