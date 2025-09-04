import time
import logging
import requests

from backend.models.common import StatName
from tests.integration.utils.data import (
    archer_template,
    goblin_template,
    simple_mission,
)
from tests.integration.utils.helpers import _create_tbs_session


def test_archer_surrounded_attack_count_and_perf(base_url: str):
    width = height = 10
    center = (5, 5)

    archer = archer_template()
    archer.id = "p.archer"
    archer.pos = center
    # Set RNG so that ALL tiles on the map are within range
    max_rng = max(
        abs(x - center[0]) + abs(y - center[1])
        for x in range(width)
        for y in range(height)
    )
    rng = max_rng
    archer.stats.base[StatName.RNG] = rng
    enemy_positions = [
        (x, y) for x in range(width) for y in range(height) if (x, y) != center
    ]

    enemies = []
    for i, pos in enumerate(enemy_positions):
        e = goblin_template()
        e.id = f"e{i}"
        e.pos = pos
        enemies.append(e)

    mission = simple_mission([archer, *enemies], width=width, height=height)

    sid, _ = _create_tbs_session(base_url, mission)

    # Warm-up and correctness check: ensure attack count equals number of enemies
    r = requests.get(
        f"{base_url}/sessions/{sid}/legal_actions",
        params={"explain": "true"},
        timeout=5,
    )
    r.raise_for_status()
    actions = r.json()["actions"]
    attack_actions = [a for a in actions if a.get("action", {}).get("kind") == "ATTACK"]
    # All enemies should be in range now
    assert len(attack_actions) == len(
        enemies
    ), f"expected {len(enemies)} attacks (all enemies in range), got {len(attack_actions)}"

    # Measure average response time over 100 requests
    N = 100
    durations = []
    for _ in range(N):
        t0 = time.perf_counter()
        rr = requests.get(
            f"{base_url}/sessions/{sid}/legal_actions",
            params={"explain": "true"},
            timeout=5,
        )
        rr.raise_for_status()
        _ = rr.json()
        durations.append((time.perf_counter() - t0) * 1000.0)  # ms

    avg_ms = sum(durations) / len(durations)
    logger = logging.getLogger(__name__)
    logger.info(
        "[perf] /sessions/%s/legal_actions?explain=true avg over %d runs: %.2f ms (enemies=%d)",
        sid,
        N,
        avg_ms,
        len(enemies),
    )
    assert (
        avg_ms < 20
    ), f"average legal_actions response {avg_ms:.2f} ms exceeds 17 ms threshold"
