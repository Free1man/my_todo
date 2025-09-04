from pydantic import BaseModel, Field

from .enums import Coord, Terrain
from .modifiers import StatModifier


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
