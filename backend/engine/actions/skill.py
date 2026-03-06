from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.skills import (
        ApplyModifierEffect,
        DamageEffect,
        HealEffect,
        Skill,
        SkillEffect,
    )
    from ..runtime import RuntimeMission, RuntimeSession, RuntimeUnit

from ...models.api import LegalAction, UseSkillAction
from ...models.enums import ActionLogResult, ActionType, SkillTarget, StatName
from ...models.evaluation import ActionEvaluation, EffectPreview
from ...models.skills import ApplyModifierEffect, DamageEffect, HealEffect
from ..logging.logger import log_event
from ..rules import (
    require_alive,
    require_ap,
    require_current_actor,
    require_in_range,
    require_unit,
)
from ..systems import pathfinding, stats
from .base import ActionHandler

DEFAULT_AREA_OFFSETS = [
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


def _skill_by_id(u: RuntimeUnit, sid: str) -> Skill | None:
    for skill in u.template.skills:
        if skill.id == sid:
            return skill
    return None


def _instanced_modifier(effect: ApplyModifierEffect):
    return effect.modifier.model_copy(deep=True)


def _skill_offsets(skill: Skill) -> list[tuple[int, int]]:
    return skill.area_offsets or DEFAULT_AREA_OFFSETS


def _target_ids(
    mission: RuntimeMission, caster: RuntimeUnit, skill: Skill, action: UseSkillAction
) -> list[str]:
    if skill.target in (SkillTarget.NONE, SkillTarget.SELF):
        return [caster.id]
    if skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT):
        return [action.target_unit_id] if action.target_unit_id else []
    if skill.target != SkillTarget.TILE or action.target_tile is None:
        return []

    tx, ty = action.target_tile
    target_ids: list[str] = []
    seen: set[str] = set()
    for dx, dy in _skill_offsets(skill):
        coord = (tx + dx, ty + dy)
        if not mission.map.in_bounds(coord):
            continue
        target = mission.unit_at(coord)
        if target and target.id not in seen:
            seen.add(target.id)
            target_ids.append(target.id)
    return target_ids


def _effect_preview_for_damage(
    target: RuntimeUnit, effect: DamageEffect
) -> tuple[EffectPreview, float]:
    before = float(target.state.hp)
    after = float(max(0, target.state.hp - effect.amount))
    return (
        EffectPreview(
            target_id=target.id,
            effect_kind=effect.kind,
            stat=StatName.HP.value,
            before=before,
            after=after,
            delta=after - before,
            note=f"{effect.damage_type.value} damage",
        ),
        before - after,
    )


def _effect_preview_for_heal(
    mission: RuntimeMission, target: RuntimeUnit, effect: HealEffect
) -> EffectPreview:
    before = float(target.state.hp)
    max_hp = float(stats.eff_stat(mission, target, StatName.MAX_HP))
    after = float(min(max_hp, target.state.hp + effect.amount))
    return EffectPreview(
        target_id=target.id,
        effect_kind=effect.kind,
        stat=StatName.HP.value,
        before=before,
        after=after,
        delta=after - before,
        note="healing",
    )


def _effect_preview_for_modifier(
    mission: RuntimeMission, target: RuntimeUnit, effect: ApplyModifierEffect
) -> EffectPreview:
    stat = effect.modifier.stat
    before = float(stats.eff_stat(mission, target, stat))
    target.state.temp_mods.append(_instanced_modifier(effect))
    mission.invalidate_cache()
    after = float(stats.eff_stat(mission, target, stat))
    return EffectPreview(
        target_id=target.id,
        effect_kind=effect.kind,
        stat=stat.value,
        before=before,
        after=after,
        delta=after - before,
        duration_turns=effect.modifier.duration_turns,
        note=f"{effect.modifier.operation.value} {effect.modifier.value}",
    )


def evaluate_skill(
    mission: RuntimeMission, action: UseSkillAction
) -> ActionEvaluation | None:
    caster = mission.units.get(action.unit_id)
    if not caster:
        return None
    skill = _skill_by_id(caster, action.skill_id)
    if skill is None:
        return None

    scratch = deepcopy(mission)
    scratch_caster = scratch.units[caster.id]
    effect_previews: list[EffectPreview] = []
    total_damage = 0.0
    target_ids = _target_ids(scratch, scratch_caster, skill, action)

    for target_id in target_ids:
        target = scratch.units[target_id]
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                preview, damage = _effect_preview_for_damage(target, effect)
                target.state.hp = int(preview.after or 0)
                total_damage += damage
                scratch.invalidate_cache()
            elif isinstance(effect, HealEffect):
                preview = _effect_preview_for_heal(scratch, target, effect)
                target.state.hp = int(preview.after or 0)
                scratch.invalidate_cache()
            else:
                preview = _effect_preview_for_modifier(scratch, target, effect)
            effect_previews.append(preview)

    summary = "No immediate effect."
    if effect_previews:
        parts = []
        for preview in effect_previews[:3]:
            stat = preview.stat or preview.effect_kind
            before = int(preview.before) if preview.before is not None else "-"
            after = int(preview.after) if preview.after is not None else "-"
            parts.append(f"{preview.target_id} {stat} {before}->{after}")
        if len(effect_previews) > 3:
            parts.append(f"+{len(effect_previews) - 3} more")
        summary = "; ".join(parts)

    return ActionEvaluation(
        action_type=ActionType.SKILL,
        attacker_id=caster.id,
        target_id=target_ids[0] if len(target_ids) == 1 else None,
        ap_cost=skill.ap_cost,
        summary=summary,
        expected_damage=total_damage,
        min_damage=total_damage,
        max_damage=total_damage,
        effects=effect_previews,
        legality_ok=True,
        illegal_reasons=[],
    )


def _apply_effect(
    mission: RuntimeMission, target: RuntimeUnit, effect: SkillEffect
) -> None:
    if isinstance(effect, DamageEffect):
        target.state.hp = max(0, target.state.hp - effect.amount)
    elif isinstance(effect, HealEffect):
        max_hp = stats.eff_stat(mission, target, StatName.MAX_HP)
        target.state.hp = min(max_hp, target.state.hp + effect.amount)
    else:
        target.state.temp_mods.append(_instanced_modifier(effect))
    mission.invalidate_cache()


class SkillHandler(ActionHandler):
    action_type = UseSkillAction

    def evaluate(self, mission, action: UseSkillAction):
        caster, reason = require_unit(mission, action.unit_id)
        if reason:
            return False, reason
        if reason := require_current_actor(mission, caster):
            return False, reason

        skill = _skill_by_id(caster, action.skill_id)
        if skill is None:
            return False, "skill not found"
        if reason := require_ap(caster, skill.ap_cost):
            return False, reason
        if caster.state.skill_cooldowns.get(skill.id, 0) > 0:
            return False, "on cooldown"
        if (
            skill.charges is not None
            and caster.state.skill_charges.get(skill.id, skill.charges) <= 0
        ):
            return False, "no charges"

        if skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT):
            if not action.target_unit_id:
                return False, "missing target"
            target, reason = require_unit(mission, action.target_unit_id)
            if reason:
                return False, "missing target"
            if reason := require_alive(target):
                return False, reason
            if (
                skill.target == SkillTarget.ALLY_UNIT
                and target.template.side != caster.template.side
            ):
                return False, "target not ally"
            if (
                skill.target == SkillTarget.ENEMY_UNIT
                and target.template.side == caster.template.side
            ):
                return False, "target not enemy"
            if reason := require_in_range(caster, target.state.pos, skill.range):
                return False, (
                    "target out of range" if reason == "out of range" else reason
                )
        elif skill.target == SkillTarget.TILE:
            if action.target_tile is None:
                return False, "missing target tile"
            if not mission.map.in_bounds(action.target_tile):
                return False, "tile out of bounds"
            if require_in_range(caster, action.target_tile, skill.range):
                return False, "tile out of range"

        return True, "ok"

    def apply(self, sess: RuntimeSession, action: UseSkillAction):
        mission = sess.mission
        caster = mission.units[action.unit_id]
        skill = _skill_by_id(caster, action.skill_id)

        caster.state.ap_left -= skill.ap_cost
        if skill.cooldown > 0:
            caster.state.skill_cooldowns[skill.id] = skill.cooldown
        if skill.charges is not None:
            caster.state.skill_charges[skill.id] = max(
                0, caster.state.skill_charges.get(skill.id, skill.charges) - 1
            )
        mission.invalidate_cache()

        for target_id in _target_ids(mission, caster, skill, action):
            target = mission.units[target_id]
            for effect in skill.effects:
                _apply_effect(mission, target, effect)

        log_event(sess, action, ActionLogResult.APPLIED)
        return sess


def enumerate_legal(mission, u: RuntimeUnit, handlers, explain: bool):
    out: list[LegalAction] = []
    for skill in u.template.skills:
        if u.state.ap_left < skill.ap_cost:
            continue
        if u.state.skill_cooldowns.get(skill.id, 0) > 0:
            continue
        if (
            skill.charges is not None
            and u.state.skill_charges.get(skill.id, skill.charges) <= 0
        ):
            continue

        def _append_if_legal(action: UseSkillAction) -> None:
            ok, why = handlers[UseSkillAction].evaluate(mission, action)
            if not ok:
                return
            evaluation = evaluate_skill(mission, action) if explain else None
            out.append(
                LegalAction(action=action, explanation=why, evaluation=evaluation)
            )

        if skill.target in (SkillTarget.SELF, SkillTarget.NONE):
            _append_if_legal(UseSkillAction(unit_id=u.id, skill_id=skill.id))
        elif skill.target == SkillTarget.ALLY_UNIT:
            for ally in mission.allies_of(u, include_self=True):
                if pathfinding.manhattan(u.state.pos, ally.state.pos) <= skill.range:
                    _append_if_legal(
                        UseSkillAction(
                            unit_id=u.id, skill_id=skill.id, target_unit_id=ally.id
                        )
                    )
        elif skill.target == SkillTarget.ENEMY_UNIT:
            for foe in mission.enemies_of(u):
                if pathfinding.manhattan(u.state.pos, foe.state.pos) <= skill.range:
                    _append_if_legal(
                        UseSkillAction(
                            unit_id=u.id, skill_id=skill.id, target_unit_id=foe.id
                        )
                    )
        elif skill.target == SkillTarget.TILE:
            for ty in range(mission.map.height):
                for tx in range(mission.map.width):
                    if pathfinding.manhattan(u.state.pos, (tx, ty)) <= skill.range:
                        _append_if_legal(
                            UseSkillAction(
                                unit_id=u.id, skill_id=skill.id, target_tile=(tx, ty)
                            )
                        )
    return out
