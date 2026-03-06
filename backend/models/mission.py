from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .enums import Coord, GoalKind, MissionStatus, Side

if TYPE_CHECKING:
    from .map import MapGrid
    from .modifiers import StatModifier
    from .units import Unit


class MissionGoal(BaseModel):
    kind: GoalKind
    survive_turns: int | None = None


class MissionEvent(BaseModel):
    id: str
    text: str


class TurnState(BaseModel):
    side_to_move: Side = Side.PLAYER
    turn: int = 1
    initiative_order: list[str] = Field(default_factory=list)
    current_unit_id: str | None = None
    status: MissionStatus = MissionStatus.IN_PROGRESS


class Mission(BaseModel):
    id: str
    name: str
    map: MapGrid
    units: dict[str, Unit]
    max_turns: int | None = None
    goals: list[MissionGoal] = Field(default_factory=list)
    pre_events: list[MissionEvent] = Field(default_factory=list)
    post_events: list[MissionEvent] = Field(default_factory=list)
    global_mods: list[StatModifier] = Field(default_factory=list)
    enemy_ai: bool = False
    turn_state: TurnState = Field(default_factory=TurnState)

    def current_unit(self) -> Unit | None:
        if not self.turn_state.current_unit_id:
            return None
        return self.units.get(self.turn_state.current_unit_id)

    def living_units(self) -> list[Unit]:
        return [u for u in self.units.values() if u.state.alive]

    def living_units_for(self, side: Side) -> list[Unit]:
        return [u for u in self.living_units() if u.template.side == side]

    def allies_of(self, unit: Unit, *, include_self: bool = False) -> list[Unit]:
        return [
            other
            for other in self.living_units_for(unit.template.side)
            if include_self or other.id != unit.id
        ]

    def enemies_of(self, unit: Unit) -> list[Unit]:
        return [
            other
            for other in self.living_units()
            if other.template.side != unit.template.side
        ]

    def units_at(
        self, coord: Coord, *, exclude_unit_id: str | None = None
    ) -> list[Unit]:
        return [
            unit
            for unit in self.units.values()
            if unit.id != exclude_unit_id
            and unit.state.alive
            and unit.state.pos == coord
        ]

    def unit_at(
        self, coord: Coord, *, exclude_unit_id: str | None = None
    ) -> Unit | None:
        units = self.units_at(coord, exclude_unit_id=exclude_unit_id)
        return units[0] if units else None

    def is_current_actor(self, unit_id: str) -> bool:
        unit = self.units.get(unit_id)
        return bool(
            unit and unit.state.alive and self.turn_state.current_unit_id == unit_id
        )

    def occupied(self, coord: Coord, *, exclude_unit_id: str | None = None) -> bool:
        return self.unit_at(coord, exclude_unit_id=exclude_unit_id) is not None


_map_module = import_module(".map", __package__)
_modifiers_module = import_module(".modifiers", __package__)
_units_module = import_module(".units", __package__)

Mission.model_rebuild(
    _types_namespace={
        "MapGrid": _map_module.MapGrid,
        "StatModifier": _modifiers_module.StatModifier,
        "Unit": _units_module.Unit,
    }
)
