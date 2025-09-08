from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ...models.map import MapGrid
    from ...models.mission import Mission
    from ...models.units import Unit

Coord = tuple[int, int]


def manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(grid: MapGrid, c: Coord) -> list[Coord]:
    x, y = c
    cand = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return [
        (nx, ny) for nx, ny in cand if 0 <= nx < grid.width and 0 <= ny < grid.height
    ]


def occupied(mission: Mission, c: Coord) -> bool:
    return any(u.alive and u.pos == c for u in mission.units.values())


def reachable_tiles(mission: Mission, u: Unit) -> set[Coord]:
    from ...models.enums import StatName
    from .stats import eff_stat

    mov = max(0, eff_stat(mission, u, StatName.MOV))
    if mov == 0:
        return set()
    grid = mission.map
    frontier: list[tuple[Coord, int]] = [(u.pos, 0)]
    seen: set[Coord] = {u.pos}
    reach: set[Coord] = {u.pos}
    while frontier:
        cur, d = frontier.pop(0)
        if d >= mov:
            continue
        for nb in neighbors(grid, cur):
            if nb in seen:
                continue
            if not grid.tile(nb).walkable:
                continue
            if occupied(mission, nb):
                continue
            seen.add(nb)
            reach.add(nb)
            frontier.append((nb, d + 1))
    return reach


def can_reach(mission: Mission, u: Unit, dst: Coord) -> bool:
    return dst in reachable_tiles(mission, u)


def diamond(center: Coord, r: int) -> Iterator[Coord]:
    cx, cy = center
    for dy in range(-r, r + 1):
        span = r - abs(dy)
        y = cy + dy
        for dx in range(-span, span + 1):
            yield (cx + dx, y)
