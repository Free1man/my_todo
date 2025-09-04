from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

Coord = tuple[int, int]  # (x, y)


class Side(str, Enum):
    PLAYER = "PLAYER"
    ENEMY = "ENEMY"
    NEUTRAL = "NEUTRAL"


class Terrain(str, Enum):
    PLAIN = "PLAIN"
    FOREST = "FOREST"
    HILL = "HILL"
    WATER = "WATER"
    BLOCKED = "BLOCKED"


class StatName(str, Enum):
    HP = "HP"
    AP = "AP"
    ATK = "ATK"
    DEF = "DEF"
    MOV = "MOV"
    RNG = "RNG"
    CRIT = "CRIT"
    INIT = "INIT"


class Operation(str, Enum):
    """
    How a modifier changes a stat:
    - ADDITIVE: add/subtract a fixed number (final = base + value)
    - MULTIPLICATIVE: scale as percentage (final = base * (1 + value/100))
    - OVERRIDE: replace base with exact value (final = value)
    """

    ADDITIVE = "ADDITIVE"
    MULTIPLICATIVE = "MULTIPLICATIVE"
    OVERRIDE = "OVERRIDE"


class ModifierSource(str, Enum):
    ITEM = "ITEM"
    AURA = "AURA"
    MAP = "MAP"
    INJURY = "INJURY"
    SKILL = "SKILL"
    GLOBAL = "GLOBAL"


class StatModifier(BaseModel):
    stat: StatName
    operation: Operation
    value: int
    source: ModifierSource = ModifierSource.GLOBAL
    tag: str | None = None
    duration_turns: int | None = None  # None = persistent while source exists


class StatBlock(BaseModel):
    base: dict[StatName, int] = Field(default_factory=dict)


class SkillKind(str, Enum):
    PASSIVE = "PASSIVE"
    ACTIVE = "ACTIVE"


class SkillTarget(str, Enum):
    SELF = "SELF"
    ENEMY_UNIT = "ENEMY_UNIT"
    ALLY_UNIT = "ALLY_UNIT"
    TILE = "TILE"
    NONE = "NONE"


class Skill(BaseModel):
    id: str
    name: str
    kind: SkillKind
    ap_cost: int = 0
    range: int = 0
    target: SkillTarget = SkillTarget.NONE
    cooldown: int = 0
    charges: int | None = None
    apply_mods: list[StatModifier] = Field(default_factory=list)
    passive_mods: list[StatModifier] = Field(default_factory=list)


class Item(BaseModel):
    id: str = "item.example"
    name: str = "Item"
    mods: list[StatModifier] = Field(default_factory=list)


class Injury(BaseModel):
    id: str
    name: str
    mods: list[StatModifier] = Field(default_factory=list)


class Aura(BaseModel):
    id: str
    name: str
    radius: int
    mods: list[StatModifier] = Field(default_factory=list)
    owner_unit_id: str | None = None


class Tile(BaseModel):
    terrain: Terrain = Terrain.PLAIN
    mods: list[StatModifier] = Field(default_factory=list)

    @property
    def walkable(self) -> bool:
        return self.terrain not in (Terrain.BLOCKED, Terrain.WATER)


class MapGrid(BaseModel):
    width: int
    height: int
    tiles: list[list[Tile]]  # tiles[y][x]

    def in_bounds(self, c: Coord) -> bool:
        x, y = c
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, c: Coord) -> Tile:
        x, y = c
        return self.tiles[y][x]


class Unit(BaseModel):
    id: str = "unit.example"
    side: Side = Side.PLAYER
    name: str = "Unit"
    pos: Coord = (0, 0)
    stats: StatBlock = Field(
        default_factory=lambda: StatBlock(
            base={
                StatName.HP: 10,
                StatName.AP: 2,
                StatName.ATK: 3,
                StatName.DEF: 1,
                StatName.MOV: 4,
                StatName.RNG: 1,
                StatName.CRIT: 5,
                StatName.INIT: 10,
            }
        )
    )
    items: list[Item] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)
    auras: list[Aura] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    alive: bool = True
    ap_left: int = 0
    skill_cooldowns: dict[str, int] = Field(default_factory=dict)
    skill_charges: dict[str, int] = Field(default_factory=dict)


class GoalKind(str, Enum):
    ELIMINATE_ALL_ENEMIES = "ELIMINATE_ALL_ENEMIES"
    SURVIVE_TURNS = "SURVIVE_TURNS"


class MissionGoal(BaseModel):
    kind: GoalKind
    survive_turns: int | None = None


class MissionStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    VICTORY = "VICTORY"
    DEFEAT = "DEFEAT"


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
