from enum import Enum

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


class SkillKind(str, Enum):
    PASSIVE = "PASSIVE"
    ACTIVE = "ACTIVE"


class SkillTarget(str, Enum):
    SELF = "SELF"
    ENEMY_UNIT = "ENEMY_UNIT"
    ALLY_UNIT = "ALLY_UNIT"
    TILE = "TILE"
    NONE = "NONE"


class GoalKind(str, Enum):
    ELIMINATE_ALL_ENEMIES = "ELIMINATE_ALL_ENEMIES"
    SURVIVE_TURNS = "SURVIVE_TURNS"


class MissionStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    VICTORY = "VICTORY"
    DEFEAT = "DEFEAT"


class TermKind(str, Enum):
    BASE = "base"
    ITEM = "item"
    ARTIFACT = "artifact"
    BUFF = "buff"
    DEBUFF = "debuff"
    STANCE = "stance"
    TERRAIN = "terrain"
    CONTEXT = "context"
    SKILL = "skill"
    OTHER = "other"


class Op(str, Enum):
    FLAT = "flat"  # +N
    MULT = "mult"  # +X% applied before final
    FINAL_MULT = "final_mult"  # +Y% applied at the very end
