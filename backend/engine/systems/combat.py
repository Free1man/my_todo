from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...models.mission import Mission
    from ...models.units import Unit

from ...models.enums import ActionType, DamageType, StatName
from ...models.evaluation import (
    ActionEvaluation,
    DamageBreakdown,
    HitChanceBreakdown,
    Penetration,
    ResistEntry,
    StatBreakdown,
    StatTerm,
)
from . import stats


def compute_damage(mission: Mission, atk: Unit, tgt: Unit) -> int:
    atk_val = stats.eff_stat(mission, atk, StatName.ATK)
    def_val = stats.eff_stat(mission, tgt, StatName.DEF)
    base = max(1, atk_val - def_val)
    crit = stats.eff_stat(mission, atk, StatName.CRIT)
    return base * 2 if crit >= 100 else base


def quick_attack_preview(mission: Mission, atk: Unit, tgt: Unit):
    predicted = compute_damage(mission, atk, tgt)
    hp_before = stats.eff_stat(mission, tgt, StatName.HP)
    hp_after = max(0, hp_before - max(predicted, 1))
    kills = hp_after == 0
    return predicted, hp_before, hp_after, kills


def apply_attack(mission: Mission, atk: Unit, tgt: Unit) -> int:
    dmg = compute_damage(mission, atk, tgt)
    hp = stats.eff_stat(mission, tgt, StatName.HP)
    hp -= max(dmg, 1)
    tgt.stats.base[StatName.HP] = max(hp, 0)
    tgt.alive = tgt.stats.base[StatName.HP] > 0
    return dmg


def evaluate_attack(
    mission: Mission, attacker_id: str, target_id: str
) -> ActionEvaluation:
    a = mission.units[attacker_id]
    t = mission.units[target_id]

    ap_cost = 1

    atk = stats.eff_stat_with_trace(mission, a, StatName.ATK)
    dfn = stats.eff_stat_with_trace(mission, t, StatName.DEF)

    pen = Penetration(flat=0.0, pct=0.0)
    effective_def = max(0.0, dfn.value * (1.0 - pen.pct) - pen.flat)

    skill_ratio = 1.0
    flat_power = 0.0
    pre_mitigation = max(0.0, atk.value - effective_def)
    raw_after_def = pre_mitigation * skill_ratio + flat_power

    vulns: list[ResistEntry] = []
    atk_mult_terms: list[StatTerm] = []

    final_before_crit = raw_after_def
    crit_stat = stats.eff_stat(mission, a, StatName.CRIT)
    crit_chance = 1.0 if crit_stat >= 100 else 0.0
    crit_mult = 2.0
    crit_expected = crit_chance * (crit_mult - 1.0) * final_before_crit

    block_flat = 0.0
    block_mult = 0.0
    after_block = max(0.0, (final_before_crit + crit_expected) - block_flat)
    after_block *= 1.0 + block_mult

    immune = False
    min_cap = 1.0
    max_cap = None
    final_capped = (
        0.0
        if immune
        else max(min_cap, after_block if max_cap is None else min(after_block, max_cap))
    )

    dmg_bd = DamageBreakdown(
        damage_type=DamageType.PHYSICAL,
        attack=atk.breakdown,
        defense=dfn.breakdown,
        penetration=pen,
        pre_mitigation=float(pre_mitigation),
        effective_defense=float(effective_def),
        raw_after_def=float(raw_after_def),
        skill_ratio=float(skill_ratio),
        flat_power=float(flat_power),
        vulnerability_mults=vulns,
        attacker_damage_mults=atk_mult_terms,
        final_before_crit=float(final_before_crit),
        crit_chance=float(crit_chance),
        crit_mult=float(crit_mult),
        crit_expected=float(crit_expected),
        block_flat=float(block_flat),
        block_mult=float(block_mult),
        final_after_block=float(after_block),
        min_cap=min_cap,
        max_cap=max_cap,
        final_capped=float(final_capped),
        immune=immune,
    )

    acc_bd = StatBreakdown(name="accuracy", base=0.0, terms=[], result=0.0)
    eva_bd = StatBreakdown(name="evasion", base=0.0, terms=[], result=0.0)
    hit_base = 100.0
    hit_mods: list[StatTerm] = []
    hit_result = 100.0
    hit_bd = HitChanceBreakdown(
        accuracy=acc_bd,
        evasion=eva_bd,
        base=hit_base,
        mods=hit_mods,
        result=hit_result,
    )

    min_dmg = max(0.0 if immune else 1.0, final_capped * 0.9)
    max_dmg = final_capped * 1.1
    summary = f"Hit {round(hit_result)}% for {int(min_dmg)}–{int(max_dmg)} (avg {final_capped:.1f}). AP:{ap_cost}"

    return ActionEvaluation(
        action_type=ActionType.ATTACK,
        attacker_id=attacker_id,
        target_id=target_id,
        ap_cost=ap_cost,
        summary=summary,
        expected_damage=float(final_capped),
        min_damage=float(min_dmg),
        max_damage=float(max_dmg),
        damage=dmg_bd,
        hit=hit_bd,
        legality_ok=True,
        illegal_reasons=[],
    )
