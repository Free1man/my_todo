from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Tuple

import requests

from backend.models.common import GoalKind, MapGrid, Mission, MissionGoal, Side, StatBlock, StatName, Terrain, Tile, Unit
from tests.integration.utils.helpers import _create_tbs_session


Coord = Tuple[int, int]
logger = logging.getLogger(__name__)


def _make_plain_map(w: int, h: int) -> MapGrid:
    return MapGrid(width=w, height=h, tiles=[[Tile(terrain=Terrain.PLAIN) for _ in range(w)] for _ in range(h)])


def _make_unit(uid: str, name: str, side: Side, pos: Coord, init: int) -> Unit:
    base = {
        StatName.HP: 12,
        StatName.AP: 2,
        StatName.ATK: 3,
        StatName.DEF: 1,
        StatName.MOV: 4,
        StatName.RNG: 1,
        StatName.CRIT: 0,
        StatName.INIT: init,
    }
    return Unit(id=uid, name=name, side=side, pos=pos, stats=StatBlock(base=base), ap_left=2)


def _spawn_line(side: Side, count: int, x: int, h: int, spacing: int = 9, init_base: int = 12) -> List[Unit]:
    units: List[Unit] = []
    ys = list(range(5, h - 5, spacing))[:count]
    for i, y in enumerate(ys):
        uid = f"{ 'p' if side == Side.PLAYER else 'e' }{i}"
        name = f"{'Ally' if side == Side.PLAYER else 'Enemy'}-{i}"
        init = init_base + (count - i)
        units.append(_make_unit(uid, name, side, (x, y), init=init))
    return units


def _build_mass_mission() -> Mission:
    W, H = 100, 100
    grid = _make_plain_map(W, H)
    allies = _spawn_line(Side.PLAYER, count=10, x=2, h=H, spacing=9, init_base=15)
    enemies = _spawn_line(Side.ENEMY, count=10, x=W - 3, h=H, spacing=9, init_base=12)
    units = {u.id: u for u in allies + enemies}
    return Mission(
        id="m.mass",
        name="Mass Battle 10v10",
        map=grid,
        units=units,
        goals=[MissionGoal(kind=GoalKind.ELIMINATE_ALL_ENEMIES)],
    )


def _manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _alive_counts(sess_json: dict) -> Tuple[int, int]:
    units: Dict[str, dict] = sess_json["mission"]["units"]
    p = sum(1 for u in units.values() if u.get("alive", True) and u["side"] == "PLAYER")
    e = sum(1 for u in units.values() if u.get("alive", True) and u["side"] == "ENEMY")
    return p, e


def _occupied_positions(sess_json: dict) -> set[Coord]:
    units: Dict[str, dict] = sess_json["mission"]["units"]
    return {tuple(u["pos"]) for u in units.values() if u.get("alive", True)}


def _choose_move_destination(sess_json: dict, target: Coord) -> Optional[Coord]:
    mission = sess_json["mission"]
    uid = mission.get("current_unit_id")
    if not uid:
        return None
    units = mission["units"]
    me = units[uid]
    me_pos = tuple(me["pos"])  # type: ignore
    mov = int(me["stats"]["base"]["MOV"])  # base MOV is fine in this setup

    # Plain map with no blocking terrain; avoid only occupied tiles
    occ = _occupied_positions(sess_json)
    occ.discard(me_pos)  # we can leave our current tile

    # Try to move in straight line towards target up to MOV tiles, preferring X direction first
    dx = 0 if target[0] == me_pos[0] else (1 if target[0] > me_pos[0] else -1)
    dy = 0 if target[1] == me_pos[1] else (1 if target[1] > me_pos[1] else -1)

    def path_clear(direction: Coord, steps: int) -> Optional[Coord]:
        x, y = me_pos
        for k in range(1, steps + 1):
            nx, ny = x + direction[0] * k, y + direction[1] * k
            c = (nx, ny)
            if c in occ:
                return None
        return (x + direction[0] * steps, y + direction[1] * steps)

    # Try longest feasible along X
    if dx != 0:
        for steps in range(mov, 0, -1):
            dest = path_clear((dx, 0), steps)
            if dest is not None:
                return dest
    # Then try along Y
    if dy != 0:
        for steps in range(mov, 0, -1):
            dest = path_clear((0, dy), steps)
            if dest is not None:
                return dest
    # If straight-line progress is blocked by units, skip moving this AP
    return None


def _apply_with_session(http: requests.Session, base_url: str, sid: str, payload: dict) -> dict:
    r = http.post(f"{base_url}/sessions/{sid}/action", json={"action": payload}, timeout=30)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        raise requests.HTTPError(
            f"{r.status_code} {r.reason} for {base_url}/sessions/{sid}/action\nPayload:\n{json.dumps(payload, indent=2)}\nResponse:\n{body}",
            response=r,
        )
    data = r.json()
    sess = data.get("session")
    if sess:
        return {"id": sess.get("id"), "mission": sess.get("mission")}
    # Fallback: if server didn't include session (it should), fetch it
    g = http.get(f"{base_url}/sessions/{sid}", timeout=30)
    g.raise_for_status()
    return g.json()


def test_mass_battle_100x100_10v10_until_victory(base_url: str):
    # 1) Build mission and create a session
    mission = _build_mass_mission()
    sid, sess = _create_tbs_session(base_url, mission)
    http = requests.Session()

    # 2) Run auto-play loop
    max_steps = 5000
    steps = 0
    last_logged_turn = 0

    while sess["mission"]["status"] == "IN_PROGRESS" and steps < max_steps:
        turn = sess["mission"]["turn"]
        if turn != last_logged_turn:
            p, e = _alive_counts(sess)
            logger.info("[mass] Turn %s: %s alive vs %s alive", turn, p, e)
            last_logged_turn = turn

        # Plan based on known setup: move toward nearest foe, attack when in range
        mission = sess["mission"]
        uid = mission.get("current_unit_id")
        if not uid:
            # should not happen; end turn to progress
            sess = _apply_with_session(http, base_url, sid, {"kind": "END_TURN"})
            steps += 1
            continue

        units = mission["units"]
        me = units[uid]
        if not me.get("alive", True):
            sess = _apply_with_session(http, base_url, sid, {"kind": "END_TURN"})
            steps += 1
            continue

        # find closest enemy
        foes = [(oid, tuple(u["pos"])) for oid, u in units.items() if u.get("alive", True) and u["side"] != me["side"]]
        if not foes:
            break
        me_pos = tuple(me["pos"])  # type: ignore
        # choose nearest by Manhattan (tie by unit id for determinism)
        target_id, target_pos = min(foes, key=lambda t: (_manhattan(me_pos, t[1]), t[0]))
        rng = int(me["stats"]["base"]["RNG"])  # base RNG is 1 in this setup
        dist = _manhattan(me_pos, target_pos)

        # Try ATTACK if in range
        if dist <= rng:
            try:
                sess = _apply_with_session(http, base_url, sid, {"kind": "ATTACK", "attacker_id": uid, "target_id": target_id})
            except requests.HTTPError:
                # likely no AP or attacker cannot act; end turn
                sess = _apply_with_session(http, base_url, sid, {"kind": "END_TURN"})
            steps += 1
            continue

        # Otherwise MOVE toward target (up to MOV tiles) or END_TURN if blocked
        dest = _choose_move_destination(sess, target_pos)
        if dest is not None:
            try:
                sess = _apply_with_session(http, base_url, sid, {"kind": "MOVE", "unit_id": uid, "to": list(dest)})
            except requests.HTTPError:
                # fallback to end turn if move rejected
                sess = _apply_with_session(http, base_url, sid, {"kind": "END_TURN"})
            steps += 1
            continue

        # No progress possible -> end turn
        sess = _apply_with_session(http, base_url, sid, {"kind": "END_TURN"})
        steps += 1

    # 3) Assertions — we should end in victory or defeat within the step budget
    status = sess["mission"]["status"]
    assert status in ("VICTORY", "DEFEAT"), f"Battle did not conclude in {max_steps} steps; status={status}"
    # Log final state
    p, e = _alive_counts(sess)
    logger.info(
        "[mass] Final: status=%s, turn=%s, %s alive vs %s alive",
        sess["mission"]["status"], sess["mission"]["turn"], p, e,
    )
