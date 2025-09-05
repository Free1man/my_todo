from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..models.enums import Side

if TYPE_CHECKING:  # typing-only imports
    from collections.abc import Sequence

    from ..models.api import Action, LegalAction
    from ..models.session import TBSSession


def enemy_autoplay(
    engine, sess: TBSSession, max_chain: int = 6, rng: random.Random | None = None
) -> tuple[int, TBSSession]:
    """Apply up to max_chain random legal actions for the current side.

    Contract:
    - Inputs: engine (has list_legal_actions(sess) and apply(sess, action)); session; max_chain; rng
    - Behavior: picks uniformly at random from legal actions each step; stops when none are available or cap reached.
    - Output: (number of actions applied, updated session).
    """
    r = rng or random
    applied = 0
    cur = sess
    while applied < max_chain:
        # Only act for enemy side; stop if it's player's turn
        if cur.mission.side_to_move != Side.ENEMY:
            break
        la = engine.list_legal_actions(cur, explain=False)
        actions: Sequence[LegalAction] = tuple(la.actions)
        if not actions:
            break
        choice = r.choice(actions)
        action: Action = choice.action
        cur = engine.apply(cur, action)
        applied += 1
    return applied, cur
