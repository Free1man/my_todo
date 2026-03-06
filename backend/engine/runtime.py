from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..models.enums import Coord, MissionStatus, Side, StatName
from ..models.mission import Mission, MissionEvent, MissionGoal, TurnState
from ..models.session import TBSSession
from ..models.units import BattleUnitState, Unit, UnitTemplate

if TYPE_CHECKING:
    from ..models.map import MapGrid
    from ..models.modifiers import StatModifier


@dataclass(slots=True)
class RuntimeUnitState:
    pos: Coord
    hp: int
    ap_left: int = 0
    temp_mods: list[StatModifier] = field(default_factory=list)
    skill_cooldowns: dict[str, int] = field(default_factory=dict)
    skill_charges: dict[str, int] = field(default_factory=dict)

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass(slots=True)
class RuntimeUnit:
    id: str
    template: UnitTemplate
    state: RuntimeUnitState


@dataclass(slots=True)
class RuntimeTurnState:
    turn: int = 1
    initiative_order: list[str] = field(default_factory=list)
    current_unit_id: str | None = None
    status: MissionStatus = MissionStatus.IN_PROGRESS


@dataclass(slots=True)
class RuntimeCache:
    occupied: dict[Coord, str] | None = None
    modifiers: dict[str, tuple[StatModifier, ...]] = field(default_factory=dict)
    stats: dict[tuple[str, StatName], int] = field(default_factory=dict)

    def clear(self) -> None:
        self.occupied = None
        self.modifiers.clear()
        self.stats.clear()


@dataclass(slots=True)
class RuntimeMission:
    id: str
    name: str
    map: MapGrid
    units: dict[str, RuntimeUnit]
    max_turns: int | None
    goals: list[MissionGoal]
    pre_events: list[MissionEvent]
    post_events: list[MissionEvent]
    global_mods: list[StatModifier]
    enemy_ai: bool
    turn_state: RuntimeTurnState
    cache: RuntimeCache = field(default_factory=RuntimeCache, repr=False)

    @property
    def side_to_move(self) -> Side | None:
        current = self.current_unit()
        return current.template.side if current else None

    def invalidate_cache(self) -> None:
        self.cache.clear()

    def current_unit(self) -> RuntimeUnit | None:
        if not self.turn_state.current_unit_id:
            return None
        unit = self.units.get(self.turn_state.current_unit_id)
        if not unit or not unit.state.alive:
            return None
        return unit

    def living_units(self) -> list[RuntimeUnit]:
        return [unit for unit in self.units.values() if unit.state.alive]

    def living_units_for(self, side: Side) -> list[RuntimeUnit]:
        return [unit for unit in self.living_units() if unit.template.side == side]

    def allies_of(
        self, unit: RuntimeUnit, *, include_self: bool = False
    ) -> list[RuntimeUnit]:
        return [
            other
            for other in self.living_units_for(unit.template.side)
            if include_self or other.id != unit.id
        ]

    def enemies_of(self, unit: RuntimeUnit) -> list[RuntimeUnit]:
        return [
            other
            for other in self.living_units()
            if other.template.side != unit.template.side
        ]

    def occupied_positions(self) -> dict[Coord, str]:
        if self.cache.occupied is not None:
            return self.cache.occupied
        occupied: dict[Coord, str] = {}
        for unit in self.living_units():
            if unit.state.pos in occupied:
                other = occupied[unit.state.pos]
                raise ValueError(
                    f"multiple living units occupy tile {unit.state.pos}: {other}, {unit.id}"
                )
            occupied[unit.state.pos] = unit.id
        self.cache.occupied = occupied
        return occupied

    def unit_at(
        self, coord: Coord, *, exclude_unit_id: str | None = None
    ) -> RuntimeUnit | None:
        unit_id = self.occupied_positions().get(coord)
        if not unit_id or unit_id == exclude_unit_id:
            return None
        return self.units.get(unit_id)

    def occupied(self, coord: Coord, *, exclude_unit_id: str | None = None) -> bool:
        return self.unit_at(coord, exclude_unit_id=exclude_unit_id) is not None

    def is_current_actor(self, unit_id: str) -> bool:
        current = self.current_unit()
        return bool(current and current.id == unit_id)


@dataclass(slots=True)
class RuntimeSession:
    id: str
    mission: RuntimeMission


def _runtime_unit(dto: Unit) -> RuntimeUnit:
    max_hp = int(
        dto.template.stats.base.get(
            StatName.MAX_HP, dto.template.stats.base.get(StatName.HP, dto.state.hp)
        )
    )
    hp = max(0, min(int(dto.state.hp), max_hp if max_hp > 0 else int(dto.state.hp)))
    return RuntimeUnit(
        id=dto.id,
        template=dto.template.model_copy(deep=True),
        state=RuntimeUnitState(
            pos=dto.state.pos,
            hp=hp,
            ap_left=dto.state.ap_left,
            temp_mods=deepcopy(dto.state.temp_mods),
            skill_cooldowns=dict(dto.state.skill_cooldowns),
            skill_charges=dict(dto.state.skill_charges),
        ),
    )


def mission_from_dto(dto: Mission) -> RuntimeMission:
    runtime = RuntimeMission(
        id=dto.id,
        name=dto.name,
        map=dto.map.model_copy(deep=True),
        units={uid: _runtime_unit(unit) for uid, unit in dto.units.items()},
        max_turns=dto.max_turns,
        goals=[goal.model_copy(deep=True) for goal in dto.goals],
        pre_events=[event.model_copy(deep=True) for event in dto.pre_events],
        post_events=[event.model_copy(deep=True) for event in dto.post_events],
        global_mods=deepcopy(dto.global_mods),
        enemy_ai=dto.enemy_ai,
        turn_state=RuntimeTurnState(
            turn=dto.turn_state.turn,
            initiative_order=list(dto.turn_state.initiative_order),
            current_unit_id=dto.turn_state.current_unit_id,
            status=dto.turn_state.status,
        ),
    )
    runtime.occupied_positions()
    return runtime


def mission_to_dto(runtime: RuntimeMission) -> Mission:
    units: dict[str, Unit] = {}
    for uid, unit in runtime.units.items():
        template = unit.template.model_copy(deep=True)
        template.stats.base.pop(StatName.HP, None)
        units[uid] = Unit(
            id=uid,
            template=template,
            state=BattleUnitState(
                pos=unit.state.pos,
                hp=unit.state.hp,
                ap_left=unit.state.ap_left,
                temp_mods=deepcopy(unit.state.temp_mods),
                skill_cooldowns=dict(unit.state.skill_cooldowns),
                skill_charges=dict(unit.state.skill_charges),
            ),
        )
    return Mission(
        id=runtime.id,
        name=runtime.name,
        map=runtime.map.model_copy(deep=True),
        units=units,
        max_turns=runtime.max_turns,
        goals=[goal.model_copy(deep=True) for goal in runtime.goals],
        pre_events=[event.model_copy(deep=True) for event in runtime.pre_events],
        post_events=[event.model_copy(deep=True) for event in runtime.post_events],
        global_mods=deepcopy(runtime.global_mods),
        enemy_ai=runtime.enemy_ai,
        turn_state=TurnState(
            turn=runtime.turn_state.turn,
            initiative_order=list(runtime.turn_state.initiative_order),
            current_unit_id=runtime.turn_state.current_unit_id,
            status=runtime.turn_state.status,
        ),
    )


def session_from_dto(sess: TBSSession) -> RuntimeSession:
    return RuntimeSession(id=sess.id, mission=mission_from_dto(sess.mission))


def session_to_dto(sess: RuntimeSession) -> TBSSession:
    return TBSSession(id=sess.id, mission=mission_to_dto(sess.mission))
