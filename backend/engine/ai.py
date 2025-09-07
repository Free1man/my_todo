from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models.api import (
    Action,
    AttackAction,
    EndTurnAction,
    LegalAction,
    MoveAction,
    UseSkillAction,
)
from ..models.enums import Side, StatName

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..models.mission import Mission


@dataclass(frozen=True)
class AIScoringWeights:
    """Tunable weights for the simple heuristic AI.

    All values are constants to avoid magic numbers scattered in logic.
    """

    lethal: float = 1000.0  # strong preference for kills
    dmg_per_ap: float = 100.0  # scale expected damage by AP efficiency
    chip_dmg: float = 1.0  # prefer any non-zero damage over nothing
    close_enemy: float = 1.0  # reward moving closer to enemies
    end_turn_bias: float = (
        -0.5
    )  # slight bias against ending turn if anything else is neutral


DEFAULT_WEIGHTS = AIScoringWeights()


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest_enemy_dist(unit_id: str, mission: Mission) -> int | None:
    self_u = mission.units.get(unit_id)
    if not self_u or not self_u.alive:
        return None
    dists: list[int] = []
    for other in mission.units.values():
        if not other.alive or other.id == self_u.id:
            continue
        if other.side == self_u.side:
            continue
        dists.append(_manhattan(self_u.pos, other.pos))
    return min(dists) if dists else None


def _nearest_enemy_dist_from(
    coord: tuple[int, int], self_side: Side, mission: Mission
) -> int | None:
    dists: list[int] = []
    for other in mission.units.values():
        if not other.alive:
            continue
        if other.side == self_side:
            continue
        dists.append(_manhattan(coord, other.pos))
    return min(dists) if dists else None


def _score_attack(
    mission: Mission, act: AttackAction, la: LegalAction, w: AIScoringWeights
) -> float:
    # Use provided evaluation if present (list_legal_actions with explain=True)
    ev = la.evaluation
    if ev is None:
        # Fallback: no evaluation; treat as small positive to avoid being worse than end turn
        return w.chip_dmg

    expected = float(ev.expected_damage)
    ap_cost = max(1.0, float(ev.ap_cost))

    # Lethality bonus using current target HP (base value; good enough for heuristic)
    atk = mission.units.get(act.attacker_id)
    tgt = mission.units.get(act.target_id)
    # Avoid attacking same-side units for now
    if atk and tgt and atk.side == tgt.side:
        return float("-1e9")
    tgt_hp = float(tgt.stats.base.get(StatName.HP, 0)) if tgt else 0.0
    lethal_bonus = w.lethal if expected >= tgt_hp and tgt_hp > 0 else 0.0

    score = lethal_bonus + w.dmg_per_ap * (expected / ap_cost)
    if expected > 0:
        score += w.chip_dmg
    return score


def _score_move(mission: Mission, act: MoveAction, w: AIScoringWeights) -> float:
    u = mission.units.get(act.unit_id)
    if not u:
        return 0.0
    before = _nearest_enemy_dist(u.id, mission)
    after = _nearest_enemy_dist_from(act.to, u.side, mission)
    if before is None or after is None:
        return 0.0
    improvement = max(0, before - after)
    return w.close_enemy * float(improvement)


def _score_skill(_: Mission, __: UseSkillAction, w: AIScoringWeights) -> float:
    # Conservatively neutral in this simple heuristic; can be expanded later.
    return 0.0


def choose_action(
    mission: Mission,
    legal_actions: Sequence[LegalAction],
    *,
    weights: AIScoringWeights = DEFAULT_WEIGHTS,
) -> Action | None:
    """Pick a single action from pre-evaluated legal actions.

    - Prefers lethal and higher expected damage per AP for attacks (when evaluation provided).
    - Prefers moving closer to enemies when no good attacks exist.
    - Otherwise slightly biases against ending turn.
    """
    best_score = float("-inf")
    best: list[Action] = []

    for la in legal_actions:
        act = la.action
        s = 0.0
        if isinstance(act, AttackAction):
            s = _score_attack(mission, act, la, weights)
        elif isinstance(act, MoveAction):
            s = _score_move(mission, act, weights)
        elif isinstance(act, UseSkillAction):
            s = _score_skill(mission, act, weights)
        elif isinstance(act, EndTurnAction):
            s = weights.end_turn_bias

        if s > best_score:
            best_score = s
            best = [act]
        elif s == best_score:
            best.append(act)

    if not best:
        return None
    # Deterministic: choose the first best encountered
    return best[0]
