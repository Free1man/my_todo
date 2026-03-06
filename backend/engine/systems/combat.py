from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime import RuntimeMission, RuntimeUnit

from ...models.enums import ActionType, DamageType, StatName
from ...models.evaluation import (
    ActionEvaluation,
    DamageBreakdown,
    EffectPreview,
    HitChanceBreakdown,
)
from . import stats


def _damage_breakdown(
    mission: RuntimeMission, atk: RuntimeUnit, tgt: RuntimeUnit
) -> tuple[int, DamageBreakdown]:
    attack_value = float(stats.eff_stat(mission, atk, StatName.ATK))
    defense_value = float(stats.eff_stat(mission, tgt, StatName.DEF))
    crit_stat = stats.eff_stat(mission, atk, StatName.CRIT)
    crit_mult = 2.0 if crit_stat >= 100 else 1.0

    effective_def = max(0.0, defense_value)
    pre_mitigation = max(1.0, attack_value - effective_def)
    final_damage = int(pre_mitigation * crit_mult)

    dmg_bd = DamageBreakdown(
        damage_type=DamageType.PHYSICAL,
        attack=attack_value,
        defense=defense_value,
        effective_defense=float(effective_def),
        raw_damage=float(pre_mitigation),
        crit_chance=1.0 if crit_mult > 1.0 else 0.0,
        crit_mult=float(crit_mult),
        final_damage=float(final_damage),
        formula=(
            f"ATK {int(attack_value)} - DEF {int(effective_def)} = "
            f"{int(pre_mitigation)}, crit x{crit_mult:.1f}"
        ),
    )
    return final_damage, dmg_bd


def compute_damage(mission: RuntimeMission, atk: RuntimeUnit, tgt: RuntimeUnit) -> int:
    damage, _ = _damage_breakdown(mission, atk, tgt)
    return damage


def quick_attack_preview(mission: RuntimeMission, atk: RuntimeUnit, tgt: RuntimeUnit):
    predicted = compute_damage(mission, atk, tgt)
    hp_before = tgt.state.hp
    hp_after = max(0, hp_before - predicted)
    kills = hp_after == 0
    return predicted, hp_before, hp_after, kills


def apply_attack(mission: RuntimeMission, atk: RuntimeUnit, tgt: RuntimeUnit) -> int:
    dmg = compute_damage(mission, atk, tgt)
    tgt.state.hp = max(0, tgt.state.hp - dmg)
    mission.invalidate_cache()
    return dmg


def evaluate_attack(
    mission: RuntimeMission, attacker_id: str, target_id: str
) -> ActionEvaluation:
    a = mission.units[attacker_id]
    t = mission.units[target_id]

    ap_cost = 1
    final_damage, dmg_bd = _damage_breakdown(mission, a, t)

    hit_base = 100.0
    hit_result = 100.0
    hit_bd = HitChanceBreakdown(
        base=hit_base,
        result=hit_result,
        formula="deterministic hit",
    )

    hp_before = float(t.state.hp)
    hp_after = float(max(0, t.state.hp - final_damage))
    summary = (
        f"Hit {round(hit_result)}% for {final_damage} damage. "
        f"Target HP {int(hp_before)} -> {int(hp_after)}. AP:{ap_cost}"
    )

    return ActionEvaluation(
        action_type=ActionType.ATTACK,
        attacker_id=attacker_id,
        target_id=target_id,
        ap_cost=ap_cost,
        summary=summary,
        expected_damage=float(final_damage),
        min_damage=float(final_damage),
        max_damage=float(final_damage),
        damage=dmg_bd,
        hit=hit_bd,
        effects=[
            EffectPreview(
                target_id=target_id,
                effect_kind="damage",
                stat=StatName.HP.value,
                before=hp_before,
                after=hp_after,
                delta=hp_after - hp_before,
                note="deterministic physical attack",
            )
        ],
        legality_ok=True,
        illegal_reasons=[],
    )
