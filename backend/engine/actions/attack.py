from __future__ import annotations

from ...models.api import AttackAction
from ...models.enums import ActionLogResult, StatName
from ...models.session import TBSSession
from ..logging.logger import log_event
from ..systems import combat, pathfinding, stats
from .base import ActionHandler


class AttackHandler(ActionHandler):
    action_type = AttackAction

    def evaluate(self, mission, action: AttackAction):
        a = mission.units.get(action.attacker_id)
        t = mission.units.get(action.target_id)
        if not a or not t:
            return False, "unknown unit(s)"
        if not a.alive or mission.current_unit_id != a.id:
            return False, "attacker cannot act"
        if a.ap_left < 1:
            return False, "no AP left"
        if not t.alive:
            return False, "target already down"
        rng = stats.eff_stat(mission, a, StatName.RNG)
        if pathfinding.manhattan(a.pos, t.pos) > rng:
            return False, "out of range"
        dmg, hp_before, hp_after, kills = combat.quick_attack_preview(mission, a, t)
        return True, (
            f"ok (predicted_damage={dmg}, target_hp_before={hp_before}, "
            f"target_hp_after={hp_after}, would_defeat={'yes' if kills else 'no'})"
        )

    def apply(self, sess: TBSSession, action: AttackAction):
        m = sess.mission
        a = m.units[action.attacker_id]
        t = m.units[action.target_id]
        combat.apply_attack(m, a, t)
        a.ap_left -= 1
        attack_eval = combat.evaluate_attack(m, a.id, t.id).model_dump(mode="json")
        log_event(sess, action, ActionLogResult.APPLIED, attack_eval=attack_eval)
        return TBSSession(id=sess.id, mission=m)
