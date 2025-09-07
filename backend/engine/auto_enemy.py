from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.enums import Side
from .ai import choose_action

if TYPE_CHECKING:  # typing-only imports
    from collections.abc import Sequence

    from ..models.api import Action, LegalAction
    from ..models.session import TBSSession


def enemy_autoplay(
    engine, sess: TBSSession, max_chain: int = 6
) -> tuple[int, TBSSession]:
    """Apply up to max_chain AI-chosen legal actions for the current side.

    Contract:
    - Inputs: engine (has list_legal_actions(sess) and apply(sess, action)); session; max_chain
    - Behavior: deterministically selects the best action by heuristic each step; stops when none are available or cap reached.
    - Output: (number of actions applied, updated session).
    """
    applied = 0
    cur = sess
    while applied < max_chain:
        # Only act for enemy side; stop if it's player's turn
        if cur.mission.side_to_move != Side.ENEMY:
            break
        # Ask for explain=True so attacks include expected_damage/AP details for scoring
        la = engine.list_legal_actions(cur, explain=True)
        actions: Sequence[LegalAction] = tuple(la.actions)
        if not actions:
            break
        picked = choose_action(cur.mission, actions)
        if picked is None:
            break
        action: Action = picked
        cur = engine.apply(cur, action)
        applied += 1
    return applied, cur
