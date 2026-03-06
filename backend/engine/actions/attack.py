from __future__ import annotations

from typing import TYPE_CHECKING

from ...models.api import AttackAction
from ...models.enums import ActionLogResult, StatName
from ..logging.logger import log_event
from ..rules import (
    require_alive,
    require_ap,
    require_current_actor,
    require_in_range,
    require_unit,
)
from ..systems import combat, stats
from .base import ActionHandler

if TYPE_CHECKING:
    from ..runtime import RuntimeSession


class AttackHandler(ActionHandler):
    action_type = AttackAction

    def evaluate(self, mission, action: AttackAction):
        a, reason = require_unit(
            mission, action.attacker_id, missing_reason="unknown unit(s)"
        )
        if reason:
            return False, reason
        t, reason = require_unit(
            mission, action.target_id, missing_reason="unknown unit(s)"
        )
        if reason:
            return False, reason
        if reason := require_current_actor(mission, a, reason="attacker cannot act"):
            return False, reason
        if reason := require_ap(a, 1):
            return False, reason
        if reason := require_alive(t):
            return False, reason
        rng = stats.eff_stat(mission, a, StatName.RNG)
        if reason := require_in_range(a, t.state.pos, rng):
            return False, reason
        dmg, hp_before, hp_after, kills = combat.quick_attack_preview(mission, a, t)
        return True, (
            f"ok (predicted_damage={dmg}, target_hp_before={hp_before}, "
            f"target_hp_after={hp_after}, would_defeat={'yes' if kills else 'no'})"
        )

    def apply(self, sess: RuntimeSession, action: AttackAction):
        m = sess.mission
        a = m.units[action.attacker_id]
        t = m.units[action.target_id]
        attack_eval = combat.evaluate_attack(m, a.id, t.id).model_dump(mode="json")
        combat.apply_attack(m, a, t)
        a.state.ap_left -= 1
        log_event(sess, action, ActionLogResult.APPLIED, attack_eval=attack_eval)
        return sess
