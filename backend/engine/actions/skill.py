from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.modifiers import StatModifier
    from ...models.units import Unit

from ...models.api import UseSkillAction
from ...models.enums import ActionLogResult, Operation, SkillTarget, StatName
from ...models.session import TBSSession
from ..logging.logger import log_event
from ..systems import pathfinding
from ..systems.effects import add_temp_mods, read_max_hp_tag
from .base import ActionHandler


def _skill_by_id(u: Unit, sid: str):
    for s in u.skills:
        if s.id == sid:
            return s
    return None


class SkillHandler(ActionHandler):
    action_type = UseSkillAction

    def evaluate(self, mission, action: UseSkillAction):
        if action.unit_id not in mission.units:
            return False, "unknown unit"
        u = mission.units[action.unit_id]
        if not u.alive or mission.current_unit_id != u.id:
            return False, "unit cannot act"
        skill = _skill_by_id(u, action.skill_id)
        if skill is None:
            return False, "skill not found"
        if u.ap_left < skill.ap_cost:
            return False, "not enough AP"
        if u.skill_cooldowns.get(skill.id, 0) > 0:
            return False, "on cooldown"
        if (
            skill.charges is not None
            and u.skill_charges.get(skill.id, skill.charges) <= 0
        ):
            return False, "no charges"

        if skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT):
            if not action.target_unit_id or action.target_unit_id not in mission.units:
                return False, "missing target"
            target = mission.units[action.target_unit_id]
            if skill.target == SkillTarget.ALLY_UNIT and target.side != u.side:
                return False, "target not ally"
            if skill.target == SkillTarget.ENEMY_UNIT and target.side == u.side:
                return False, "target not enemy"
            if pathfinding.manhattan(u.pos, target.pos) > skill.range:
                return False, "target out of range"
        elif skill.target == SkillTarget.TILE:
            if action.target_tile is None:
                return False, "missing target tile"
            if not mission.map.in_bounds(action.target_tile):
                return False, "tile out of bounds"
            if pathfinding.manhattan(u.pos, action.target_tile) > skill.range:
                return False, "tile out of range"
        return True, "ok"

    def apply(self, sess: TBSSession, action: UseSkillAction):
        mission = sess.mission
        u = mission.units[action.unit_id]
        skill = _skill_by_id(u, action.skill_id)
        u.ap_left -= skill.ap_cost
        if skill.cooldown > 0:
            u.skill_cooldowns[skill.id] = skill.cooldown + 1
        if skill.charges is not None:
            u.skill_charges[skill.id] = max(
                0, u.skill_charges.get(skill.id, skill.charges) - 1
            )

        def _apply_hp_with_cap(
            target_unit: Unit, delta: int | None, override: int | None = None
        ):
            max_hp_cap = read_max_hp_tag(target_unit)
            if delta is not None:
                cur = target_unit.stats.base.get(StatName.HP, 0)
                new_hp = cur + delta
                if max_hp_cap is not None:
                    new_hp = min(max_hp_cap, new_hp)
                target_unit.stats.base[StatName.HP] = max(0, new_hp)
                target_unit.alive = target_unit.stats.base[StatName.HP] > 0
            if override is not None:
                val = override
                if max_hp_cap is not None:
                    val = min(max_hp_cap, val)
                target_unit.stats.base[StatName.HP] = max(0, val)
                target_unit.alive = target_unit.stats.base[StatName.HP] > 0

        if skill.target == SkillTarget.TILE and action.target_tile is not None:
            tx, ty = action.target_tile
            hp_delta = None
            for m in skill.apply_mods or []:
                if m.stat == StatName.HP and m.operation == Operation.ADDITIVE:
                    hp_delta = m.value
                    break
            offsets = action.area_offsets or [
                (-1, -1),
                (-1, 0),
                (-1, 1),
                (0, -1),
                (0, 0),
                (0, 1),
                (1, -1),
                (1, 0),
                (1, 1),
            ]
            for dx, dy in offsets:
                x, y = tx + dx, ty + dy
                if not mission.map.in_bounds((x, y)):
                    continue
                for t in mission.units.values():
                    if not t.alive or t.pos != (x, y):
                        continue
                    if hp_delta is not None:
                        if hp_delta < 0 and t.side == u.side:
                            continue
                        if hp_delta > 0 and t.side != u.side:
                            continue
                        _apply_hp_with_cap(t, hp_delta)
                    temp_mods: list[StatModifier] = []
                    for m in skill.apply_mods or []:
                        if m.stat == StatName.HP:
                            continue
                        if (
                            m.operation == Operation.ADDITIVE
                            and m.value < 0
                            and t.side == u.side
                        ):
                            continue
                        if (
                            m.operation == Operation.ADDITIVE
                            and m.value > 0
                            and t.side != u.side
                        ):
                            continue
                        temp_mods.append(m)
                    if temp_mods:
                        add_temp_mods(t, temp_mods)
        else:
            target_unit = u
            if (
                skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT)
                and action.target_unit_id
            ):
                target_unit = mission.units[action.target_unit_id]
            temp_mods: list[StatModifier] = []
            hp_add: int | None = None
            hp_override: int | None = None
            for m in skill.apply_mods or []:
                if m.stat == StatName.HP:
                    if m.operation == Operation.ADDITIVE:
                        hp_add = (hp_add or 0) + m.value
                    elif m.operation == Operation.OVERRIDE:
                        hp_override = m.value
                    else:
                        temp_mods.append(m)
                else:
                    temp_mods.append(m)
            _apply_hp_with_cap(target_unit, hp_add, hp_override)
            if temp_mods:
                add_temp_mods(target_unit, temp_mods)

        log_event(sess, action, ActionLogResult.APPLIED)
        return TBSSession(id=sess.id, mission=mission)


def enumerate_legal(mission, u: Unit, handlers, explain: bool):
    from ...models.api import LegalAction, UseSkillAction

    out: list[LegalAction] = []
    for s in u.skills:
        if u.ap_left < s.ap_cost:
            continue
        if u.skill_cooldowns.get(s.id, 0) > 0:
            continue
        if s.charges is not None and u.skill_charges.get(s.id, s.charges) <= 0:
            continue
        if s.target in (SkillTarget.SELF, SkillTarget.NONE):
            act = UseSkillAction(unit_id=u.id, skill_id=s.id)
            ok, why = handlers[UseSkillAction].evaluate(mission, act)
            if ok:
                out.append(LegalAction(action=act, explanation=why))
        elif s.target == SkillTarget.ALLY_UNIT:
            for ally in mission.units.values():
                if not ally.alive or ally.side != u.side:
                    continue
                if pathfinding.manhattan(u.pos, ally.pos) <= s.range:
                    act = UseSkillAction(
                        unit_id=u.id, skill_id=s.id, target_unit_id=ally.id
                    )
                    ok, why = handlers[UseSkillAction].evaluate(mission, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))
        elif s.target == SkillTarget.ENEMY_UNIT:
            for foe in mission.units.values():
                if not foe.alive or foe.side == u.side:
                    continue
                if pathfinding.manhattan(u.pos, foe.pos) <= s.range:
                    act = UseSkillAction(
                        unit_id=u.id, skill_id=s.id, target_unit_id=foe.id
                    )
                    ok, why = handlers[UseSkillAction].evaluate(mission, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))
        elif s.target == SkillTarget.TILE:
            for ty in range(mission.map.height):
                for tx in range(mission.map.width):
                    if pathfinding.manhattan(u.pos, (tx, ty)) <= s.range:
                        act = UseSkillAction(
                            unit_id=u.id, skill_id=s.id, target_tile=(tx, ty)
                        )
                        ok, why = handlers[UseSkillAction].evaluate(mission, act)
                        if ok:
                            out.append(LegalAction(action=act, explanation=why))
    return out
