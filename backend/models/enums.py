from enum import Enum

Coord = tuple[int, int]  # (x, y)


class Side(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


class Terrain(str, Enum):
    PLAIN = "plain"
    FOREST = "forest"
    HILL = "hill"
    WATER = "water"
    BLOCKED = "blocked"


class StatName(str, Enum):
    HP = "hp"
    AP = "ap"
    ATK = "atk"
    DEF = "def"
    MOV = "mov"
    RNG = "rng"
    CRIT = "crit"
    INIT = "init"


class Operation(str, Enum):
    """
    How a modifier changes a stat:
    - ADDITIVE: add/subtract a fixed number (final = base + value)
    - MULTIPLICATIVE: scale as percentage (final = base * (1 + value/100))
    - OVERRIDE: replace base with exact value (final = value)
    """

    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    OVERRIDE = "override"


class ModifierSource(str, Enum):
    ITEM = "item"
    AURA = "aura"
    MAP = "map"
    INJURY = "injury"
    SKILL = "skill"
    GLOBAL = "global"


class SkillKind(str, Enum):
    PASSIVE = "passive"
    ACTIVE = "active"


class SkillTarget(str, Enum):
    SELF = "self"
    ENEMY_UNIT = "enemy_unit"
    ALLY_UNIT = "ally_unit"
    TILE = "tile"
    NONE = "none"


class GoalKind(str, Enum):
    ELIMINATE_ALL_ENEMIES = "eliminate_all_enemies"
    SURVIVE_TURNS = "survive_turns"


class MissionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    VICTORY = "victory"
    DEFEAT = "defeat"


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


class DamageType(str, Enum):
    PHYSICAL = "physical"
    MAGIC = "magic"
    TRUE = "true"


class ActionType(str, Enum):
    ATTACK = "attack"
    SKILL = "skill"
    ITEM = "item"
    WAIT = "wait"


class ActionKind(str, Enum):
    MOVE = "move"
    ATTACK = "attack"
    USE_SKILL = "use_skill"
    end_turn = "end_turn"
