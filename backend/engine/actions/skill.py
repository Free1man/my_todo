from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.modifiers import StatModifier
    from ...models.units import Unit

from ...models.api import LegalAction, UseSkillAction
from ...models.enums import ActionLogResult, Operation, SkillTarget, StatName
from ...models.session import TBSSession
from ..logging.logger import log_event
from ..systems import pathfinding, stats
from .base import ActionHandler


def _skill_by_id(u: Unit, sid: str):
    for s in u.template.skills:
        if s.id == sid:
            return s
    return None


def _instanced_modifier(mod: StatModifier) -> StatModifier:
    """Detach applied effects from the skill template so each target tracks duration independently."""
    return mod.model_copy(deep=True)


def _split_applied_effects(
    skill,
) -> tuple[int | None, int | None, list[StatModifier]]:
    hp_add: int | None = None
    hp_override: int | None = None
    temp_mods: list[StatModifier] = []
    for mod in skill.apply_mods or []:
        if mod.stat == StatName.HP:
            if mod.operation == Operation.ADDITIVE:
                hp_add = (hp_add or 0) + mod.value
                continue
            if mod.operation == Operation.OVERRIDE:
                hp_override = mod.value
                continue
        temp_mods.append(mod)
    return hp_add, hp_override, temp_mods


class SkillHandler(ActionHandler):
    action_type = UseSkillAction

    def evaluate(self, mission, action: UseSkillAction):
        if action.unit_id not in mission.units:
            return False, "unknown unit"
        u = mission.units[action.unit_id]
        if not mission.is_current_actor(u.id):
            return False, "unit cannot act"
        skill = _skill_by_id(u, action.skill_id)
        if skill is None:
            return False, "skill not found"
        if u.state.ap_left < skill.ap_cost:
            return False, "not enough AP"
        if u.state.skill_cooldowns.get(skill.id, 0) > 0:
            return False, "on cooldown"
        if (
            skill.charges is not None
            and u.state.skill_charges.get(skill.id, skill.charges) <= 0
        ):
            return False, "no charges"

        if skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT):
            if not action.target_unit_id or action.target_unit_id not in mission.units:
                return False, "missing target"
            target = mission.units[action.target_unit_id]
            if (
                skill.target == SkillTarget.ALLY_UNIT
                and target.template.side != u.template.side
            ):
                return False, "target not ally"
            if (
                skill.target == SkillTarget.ENEMY_UNIT
                and target.template.side == u.template.side
            ):
                return False, "target not enemy"
            if pathfinding.manhattan(u.state.pos, target.state.pos) > skill.range:
                return False, "target out of range"
        elif skill.target == SkillTarget.TILE:
            if action.target_tile is None:
                return False, "missing target tile"
            if not mission.map.in_bounds(action.target_tile):
                return False, "tile out of bounds"
            if pathfinding.manhattan(u.state.pos, action.target_tile) > skill.range:
                return False, "tile out of range"
        return True, "ok"

    def apply(self, sess: TBSSession, action: UseSkillAction):
        mission = sess.mission
        u = mission.units[action.unit_id]
        skill = _skill_by_id(u, action.skill_id)
        u.state.ap_left -= skill.ap_cost
        if skill.cooldown > 0:
            u.state.skill_cooldowns[skill.id] = skill.cooldown
        if skill.charges is not None:
            u.state.skill_charges[skill.id] = max(
                0, u.state.skill_charges.get(skill.id, skill.charges) - 1
            )

        def _apply_hp_with_cap(
            target_unit: Unit, delta: int | None, override: int | None = None
        ):
            max_hp_cap = stats.eff_stat(mission, target_unit, StatName.MAX_HP)
            if delta is not None:
                cur = target_unit.template.stats.base.get(StatName.HP, 0)
                new_hp = cur + delta
                new_hp = min(max_hp_cap, new_hp)
                target_unit.template.stats.base[StatName.HP] = max(0, new_hp)
                target_unit.state.alive = (
                    target_unit.template.stats.base[StatName.HP] > 0
                )
            if override is not None:
                val = override
                val = min(max_hp_cap, val)
                target_unit.template.stats.base[StatName.HP] = max(0, val)
                target_unit.state.alive = (
                    target_unit.template.stats.base[StatName.HP] > 0
                )

        hp_add, hp_override, temp_mod_bases = _split_applied_effects(skill)

        if skill.target == SkillTarget.TILE and action.target_tile is not None:
            tx, ty = action.target_tile
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
                for target_unit in mission.units_at((x, y)):
                    _apply_hp_with_cap(target_unit, hp_add, hp_override)
                    temp_mods = [_instanced_modifier(mod) for mod in temp_mod_bases]
                    if temp_mods:
                        target_unit.state.temp_mods.extend(temp_mods)
        else:
            target_unit = u
            if (
                skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT)
                and action.target_unit_id
            ):
                target_unit = mission.units[action.target_unit_id]
            temp_mods = [_instanced_modifier(mod) for mod in temp_mod_bases]
            _apply_hp_with_cap(target_unit, hp_add, hp_override)
            if temp_mods:
                target_unit.state.temp_mods.extend(temp_mods)

        log_event(sess, action, ActionLogResult.APPLIED)
        return TBSSession(id=sess.id, mission=mission)


def enumerate_legal(mission, u: Unit, handlers, explain: bool):
    out: list[LegalAction] = []
    for s in u.template.skills:
        if u.state.ap_left < s.ap_cost:
            continue
        if u.state.skill_cooldowns.get(s.id, 0) > 0:
            continue
        if s.charges is not None and u.state.skill_charges.get(s.id, s.charges) <= 0:
            continue
        if s.target in (SkillTarget.SELF, SkillTarget.NONE):
            act = UseSkillAction(unit_id=u.id, skill_id=s.id)
            ok, why = handlers[UseSkillAction].evaluate(mission, act)
            if ok:
                out.append(LegalAction(action=act, explanation=why))
        elif s.target == SkillTarget.ALLY_UNIT:
            for ally in mission.allies_of(u, include_self=True):
                if pathfinding.manhattan(u.state.pos, ally.state.pos) <= s.range:
                    act = UseSkillAction(
                        unit_id=u.id, skill_id=s.id, target_unit_id=ally.id
                    )
                    ok, why = handlers[UseSkillAction].evaluate(mission, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))
        elif s.target == SkillTarget.ENEMY_UNIT:
            for foe in mission.enemies_of(u):
                if pathfinding.manhattan(u.state.pos, foe.state.pos) <= s.range:
                    act = UseSkillAction(
                        unit_id=u.id, skill_id=s.id, target_unit_id=foe.id
                    )
                    ok, why = handlers[UseSkillAction].evaluate(mission, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))
        elif s.target == SkillTarget.TILE:
            for ty in range(mission.map.height):
                for tx in range(mission.map.width):
                    if pathfinding.manhattan(u.state.pos, (tx, ty)) <= s.range:
                        act = UseSkillAction(
                            unit_id=u.id, skill_id=s.id, target_tile=(tx, ty)
                        )
                        ok, why = handlers[UseSkillAction].evaluate(mission, act)
                        if ok:
                            out.append(LegalAction(action=act, explanation=why))
    return out
