from __future__ import annotations

from pydantic import BaseModel

from ..models.api import (
    Action,
    AttackAction,
    EndTurnAction,
    EvaluateResponse,
    LegalAction,
    LegalActionsResponse,
    MoveAction,
    UseSkillAction,
)
from ..models.enums import (
    ActionType,
    DamageType,
    GoalKind,
    MissionStatus,
    ModifierSource,
    Operation,
    Side,
    SkillTarget,
    StatName,
    TermKind,
)
from ..models.evaluation import (
    ActionEvaluation,
    DamageBreakdown,
    HitChanceBreakdown,
    Penetration,
    ResistEntry,
    StatBreakdown,
    StatTerm,
)
from ..models.map import MapGrid
from ..models.mission import Mission
from ..models.modifiers import StatModifier
from ..models.session import TBSSession
from ..models.units import Unit

Coord = tuple[int, int]


class TBSEngine:
    # ---------- Public API ----------

    def evaluate(self, sess: TBSSession, action: Action) -> EvaluateResponse:
        legal, reason = self._evaluate_action(sess.mission, action)
        return EvaluateResponse(legal=legal, explanation=reason)

    def apply(self, sess: TBSSession, action: Action) -> TBSSession:
        mission = sess.mission
        if isinstance(action, MoveAction):
            u = mission.units[action.unit_id]
            u.pos = action.to
            u.ap_left -= 1

        elif isinstance(action, AttackAction):
            atk = mission.units[action.attacker_id]
            tgt = mission.units[action.target_id]
            dmg = self._compute_damage(mission, atk, tgt)
            hp = self._eff_stat(mission, tgt, StatName.HP)
            hp -= max(dmg, 1)
            tgt.stats.base[StatName.HP] = max(hp, 0)
            if tgt.stats.base[StatName.HP] == 0:
                tgt.alive = False
            atk.ap_left -= 1

        elif isinstance(action, UseSkillAction):
            u = mission.units[action.unit_id]
            skill = self._skill_by_id(u, action.skill_id)
            u.ap_left -= skill.ap_cost
            if skill.cooldown > 0:
                u.skill_cooldowns[skill.id] = skill.cooldown + 1
            if skill.charges is not None:
                u.skill_charges[skill.id] = max(
                    0, u.skill_charges.get(skill.id, skill.charges) - 1
                )
            if skill.apply_mods:
                # Determine the unit that will receive the skill's effects
                target_unit = u
                if (
                    skill.target in (SkillTarget.ALLY_UNIT, SkillTarget.ENEMY_UNIT)
                    and action.target_unit_id
                ):
                    target_unit = mission.units[action.target_unit_id]

                # Split HP-direct effects vs. temporary modifiers
                temp_mods: list[StatModifier] = []

                # Helper: read MAX_HP tag if present to cap heals
                def _max_hp_from_tags(unit: Unit) -> int | None:
                    for tag in unit.tags:
                        if isinstance(tag, str) and tag.startswith("MAX_HP="):
                            try:
                                return int(tag.split("=", 1)[1])
                            except Exception:
                                return None
                    return None

                max_hp_cap = _max_hp_from_tags(target_unit)

                for m in skill.apply_mods:
                    if m.stat == StatName.HP:
                        # Directly modify base HP for healing/damage skills
                        if m.operation == Operation.ADDITIVE:
                            cur = target_unit.stats.base.get(StatName.HP, 0)
                            new_hp = cur + m.value
                            if max_hp_cap is not None:
                                new_hp = min(max_hp_cap, new_hp)
                            target_unit.stats.base[StatName.HP] = max(0, new_hp)
                        elif m.operation == Operation.OVERRIDE:
                            val = m.value
                            if max_hp_cap is not None:
                                val = min(max_hp_cap, val)
                            target_unit.stats.base[StatName.HP] = max(0, val)
                        else:
                            # Multiplicative and others are treated as temporary mods to HP
                            temp_mods.append(m)
                    else:
                        temp_mods.append(m)

                if temp_mods:
                    self._attach_temp_mods(target_unit, temp_mods)

        elif isinstance(action, EndTurnAction):
            self._end_turn(mission)

        return TBSSession(id=sess.id, mission=mission)

    def list_legal_actions(
        self, sess: TBSSession, *, explain: bool = False
    ) -> LegalActionsResponse:
        """
        Enumerate all legal actions for the side-to-move and return them
        pre-evaluated with explanations (so clients do not spam /evaluate).
        """
        m = sess.mission
        out: list[LegalAction] = []

        added_end_turn = False

        for u in m.units.values():
            if not u.alive or u.id != m.current_unit_id:
                continue

            # end_turn: show once per turn
            if not added_end_turn:
                ok, why = self._evaluate_action(m, EndTurnAction())
                if ok:
                    out.append(LegalAction(action=EndTurnAction(), explanation=why))
                    added_end_turn = True

            # Units must have AP to do unit-bound actions
            if u.ap_left < 1:
                continue

            # MOVES
            for dst in self._reachable_tiles(m, u):
                if dst == u.pos:
                    continue
                act = MoveAction(unit_id=u.id, to=dst)
                ok, why = self._evaluate_action(m, act)
                if ok:
                    out.append(LegalAction(action=act, explanation=why))

            # ATTACKS
            rng = self._eff_stat(m, u, StatName.RNG)
            for other in m.units.values():
                if not other.alive or other.id == u.id:
                    continue
                if manhattan(u.pos, other.pos) <= rng:
                    act = AttackAction(attacker_id=u.id, target_id=other.id)
                    ok, why = self._evaluate_action(m, act)
                    if ok:
                        evaluation = (
                            self.evaluate_attack(m, act.attacker_id, act.target_id)
                            if explain
                            else None
                        )
                        out.append(
                            LegalAction(
                                action=act, explanation=why, evaluation=evaluation
                            )
                        )

            # SKILLS
            for s in u.skills:
                # cost/cooldown/charges checks
                if u.ap_left < s.ap_cost:
                    continue
                if u.skill_cooldowns.get(s.id, 0) > 0:
                    continue
                if s.charges is not None and u.skill_charges.get(s.id, s.charges) <= 0:
                    continue

                if s.target in (SkillTarget.SELF, SkillTarget.NONE):
                    act = UseSkillAction(unit_id=u.id, skill_id=s.id)
                    ok, why = self._evaluate_action(m, act)
                    if ok:
                        out.append(LegalAction(action=act, explanation=why))

                elif s.target == SkillTarget.ALLY_UNIT:
                    for ally in m.units.values():
                        if not ally.alive or ally.side != u.side:
                            continue
                        if manhattan(u.pos, ally.pos) <= s.range:
                            act = UseSkillAction(
                                unit_id=u.id, skill_id=s.id, target_unit_id=ally.id
                            )
                            ok, why = self._evaluate_action(m, act)
                            if ok:
                                out.append(LegalAction(action=act, explanation=why))

                elif s.target == SkillTarget.ENEMY_UNIT:
                    for foe in m.units.values():
                        if not foe.alive or foe.side == u.side:
                            continue
                        if manhattan(u.pos, foe.pos) <= s.range:
                            act = UseSkillAction(
                                unit_id=u.id, skill_id=s.id, target_unit_id=foe.id
                            )
                            ok, why = self._evaluate_action(m, act)
                            if ok:
                                out.append(LegalAction(action=act, explanation=why))

                # TILE target omitted in demo (engine's apply ignores TILE for now)

        return LegalActionsResponse(actions=out)

    # ---------- Internal helpers ----------

    # ---------- Explainable stat tracing ----------
    class EffStat(BaseModel):
        value: float
        breakdown: StatBreakdown

    def _map_source_to_kind(self, src: ModifierSource | None) -> TermKind:
        if src == ModifierSource.ITEM:
            return TermKind.ITEM
        if src == ModifierSource.AURA:
            return TermKind.BUFF
        if src == ModifierSource.MAP:
            return TermKind.TERRAIN
        if src == ModifierSource.INJURY:
            return TermKind.DEBUFF
        if src == ModifierSource.SKILL:
            return TermKind.SKILL
        # GLOBAL or unknown
        return TermKind.CONTEXT

    def _eff_stat_with_trace(
        self, mission: Mission, u: Unit, stat: StatName
    ) -> TBSEngine.EffStat:
        base_val = u.stats.base.get(stat, 0)

        # Collect modifiers exactly like _eff_stat
        all_mods: list[StatModifier] = []
        for it in u.items:
            all_mods.extend(it.mods)
        for inj in u.injuries:
            all_mods.extend(inj.mods)
        for a in u.auras:
            all_mods.extend(a.mods)
        for other in mission.units.values():
            if not other.alive or other.id == u.id:
                continue
            if not other.auras:
                continue
            d = manhattan(u.pos, other.pos)
            for a in other.auras:
                if d <= (a.radius or 0):
                    all_mods.extend(a.mods)
        all_mods.extend(mission.map.tile(u.pos).mods)
        for s in u.skills:
            all_mods.extend(s.passive_mods)
        all_mods.extend(mission.global_mods)

        add_flat = 0
        mul = 1.0
        override: int | None = None
        terms: list[StatTerm] = []

        for m in all_mods:
            if m.stat != stat:
                continue
            kind = self._map_source_to_kind(m.source)
            if m.operation == Operation.ADDITIVE:
                add_flat += m.value
                terms.append(
                    StatTerm(
                        kind=kind,
                        source=m.source.value if m.source else "context",
                        op=Operation.ADDITIVE,
                        value=float(m.value),
                    )
                )
            elif m.operation == Operation.MULTIPLICATIVE:
                mul *= 1.0 + (m.value / 100.0)
                terms.append(
                    StatTerm(
                        kind=kind,
                        source=m.source.value if m.source else "context",
                        op=Operation.MULTIPLICATIVE,
                        value=float(m.value) / 100.0,
                    )
                )
            elif m.operation == Operation.OVERRIDE:
                override = m.value
                # Represent override as a flat delta for transparency
                delta = float(m.value - base_val)
                terms.append(
                    StatTerm(
                        kind=kind,
                        source=m.source.value if m.source else "context",
                        op=Operation.ADDITIVE,
                        value=delta,
                        note="override",
                    )
                )

        base_applied = override if override is not None else base_val
        result = max(int(base_applied * mul) + add_flat, 0)

        bd = StatBreakdown(
            name=stat.value.lower(),
            base=float(base_val),
            terms=terms,
            result=float(result),
        )
        return TBSEngine.EffStat(value=float(result), breakdown=bd)

    # ---- Public initializer (use this from app.py) ----
    def initialize_mission(self, mission: Mission) -> None:
        """Compute initiative order deterministically and prime the active unit with full AP.
        If current_unit_id is provided, rotate the order so that it is first; otherwise pick first by INIT.
        """
        # Fresh recompute from stats
        requested_cursor = mission.current_unit_id
        self._recompute_initiative_order(mission)
        # Record each unit's initial max HP in tags for healing caps
        for _u in mission.units.values():
            try:
                if not any(
                    isinstance(t, str) and t.startswith("MAX_HP=") for t in _u.tags
                ):
                    base_hp = _u.stats.base.get(StatName.HP, 0)
                    _u.tags.append(f"MAX_HP={base_hp}")
            except Exception:
                pass
        # If a cursor was provided, rotate order to start there (if alive and present)
        if requested_cursor and requested_cursor in mission.initiative_order:
            idx = mission.initiative_order.index(requested_cursor)
            mission.initiative_order = (
                mission.initiative_order[idx:] + mission.initiative_order[:idx]
            )
        # Set current to first in order
        mission.current_unit_id = (
            mission.initiative_order[0] if mission.initiative_order else None
        )
        # Prime AP for the current unit if alive
        if mission.current_unit_id:
            u = mission.units.get(mission.current_unit_id)
            if u and u.alive:
                u.ap_left = self._eff_stat(mission, u, StatName.AP)
                mission.side_to_move = u.side

    def _evaluate_action(self, mission: Mission, action: Action) -> tuple[bool, str]:
        if isinstance(action, MoveAction):
            if action.unit_id not in mission.units:
                return False, "unknown unit"
            u = mission.units[action.unit_id]
            if not self._unit_can_act(mission, u):
                return False, "unit cannot act"
            if u.ap_left < 1:
                return False, "no AP left"
            path_ok = self._can_reach(mission, u, action.to)
            return (True, "ok") if path_ok else (False, "cannot reach")

        if isinstance(action, AttackAction):
            if (
                action.attacker_id not in mission.units
                or action.target_id not in mission.units
            ):
                return False, "unknown unit(s)"
            atk = mission.units[action.attacker_id]
            tgt = mission.units[action.target_id]
            if not self._unit_can_act(mission, atk):
                return False, "attacker cannot act"
            if atk.ap_left < 1:
                return False, "no AP left"
            if not tgt.alive:
                return False, "target already down"
            rng = self._eff_stat(mission, atk, StatName.RNG)
            if manhattan(atk.pos, tgt.pos) > rng:
                return False, "out of range"

            predicted = self._compute_damage(mission, atk, tgt)
            hp_before = self._eff_stat(mission, tgt, StatName.HP)
            hp_after = max(0, hp_before - max(predicted, 1))
            kills = "yes" if hp_after == 0 else "no"
            return True, (
                f"ok (predicted_damage={predicted}, target_hp_before={hp_before}, "
                f"target_hp_after={hp_after}, would_defeat={kills})"
            )

        if isinstance(action, UseSkillAction):
            if action.unit_id not in mission.units:
                return False, "unknown unit"
            u = mission.units[action.unit_id]
            if not self._unit_can_act(mission, u):
                return False, "unit cannot act"
            skill = self._skill_by_id(u, action.skill_id)
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
                if (
                    not action.target_unit_id
                    or action.target_unit_id not in mission.units
                ):
                    return False, "missing target"
                target = mission.units[action.target_unit_id]
                if skill.target == SkillTarget.ALLY_UNIT and target.side != u.side:
                    return False, "target not ally"
                if skill.target == SkillTarget.ENEMY_UNIT and target.side == u.side:
                    return False, "target not enemy"
                if manhattan(u.pos, target.pos) > skill.range:
                    return False, "target out of range"
            return True, "ok"

        if isinstance(action, EndTurnAction):
            return True, "ok"

        return False, "unknown action"

    def _unit_can_act(self, mission: Mission, u: Unit) -> bool:
        if not u.alive:
            return False
        # If initiative is set, only the current unit can act.
        if mission.current_unit_id:
            return mission.current_unit_id == u.id
        # Fallback: if no unit is active, no unit can act.
        return False

    def _neighbors(self, grid: MapGrid, c: Coord) -> list[Coord]:
        x, y = c
        cand = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return [
            (nx, ny)
            for nx, ny in cand
            if 0 <= nx < grid.width and 0 <= ny < grid.height
        ]

    def _occupied(self, mission: Mission, c: Coord) -> bool:
        return any(u.alive and u.pos == c for u in mission.units.values())

    def _reachable_tiles(self, mission: Mission, u: Unit) -> set[Coord]:
        mov = max(0, self._eff_stat(mission, u, StatName.MOV))
        if mov == 0:
            return set()
        grid = mission.map
        frontier: list[tuple[Coord, int]] = [(u.pos, 0)]
        seen: set[Coord] = {u.pos}
        reach: set[Coord] = {u.pos}
        while frontier:
            cur, d = frontier.pop(0)
            if d >= mov:
                continue
            for nb in self._neighbors(grid, cur):
                if nb in seen:
                    continue
                if not grid.tile(nb).walkable:
                    continue
                if self._occupied(mission, nb):
                    # allow stepping ONTO an occupied tile only if it's the origin (staying put) — which we skip later
                    continue
                seen.add(nb)
                reach.add(nb)
                frontier.append((nb, d + 1))
        return reach

    def _can_reach(self, mission: Mission, u: Unit, dst: Coord) -> bool:
        return dst in self._reachable_tiles(mission, u)

    def _eff_stat(self, mission: Mission, u: Unit, stat: StatName) -> int:
        value = u.stats.base.get(stat, 0)

        def apply_mods(mods: list[StatModifier], cur: int) -> int:
            add = 0
            mul = 1.0
            override: int | None = None
            for m in mods:
                if m.stat != stat:
                    continue
                if m.operation == Operation.ADDITIVE:
                    add += m.value
                elif m.operation == Operation.MULTIPLICATIVE:
                    mul *= 1.0 + (m.value / 100.0)
                elif m.operation == Operation.OVERRIDE:
                    override = m.value
            base = cur if override is None else override
            return max(int(base * mul) + add, 0)

        all_mods: list[StatModifier] = []
        # items & injuries attached to this unit
        for it in u.items:
            all_mods.extend(it.mods)
        for inj in u.injuries:
            all_mods.extend(inj.mods)

        # auras attached to self
        for a in u.auras:
            all_mods.extend(a.mods)
        # auras emitted by nearby living units within radius
        for other in mission.units.values():
            if not other.alive or other.id == u.id:
                continue
            if not other.auras:
                continue
            d = manhattan(u.pos, other.pos)
            for a in other.auras:
                if d <= (a.radius or 0):
                    all_mods.extend(a.mods)

        # tile effects
        all_mods.extend(mission.map.tile(u.pos).mods)
        # passive skills
        for s in u.skills:
            all_mods.extend(s.passive_mods)
        # mission/global
        all_mods.extend(mission.global_mods)

        return apply_mods(all_mods, value)

    def _compute_damage(self, mission: Mission, atk: Unit, tgt: Unit) -> int:
        atk_val = self._eff_stat(mission, atk, StatName.ATK)
        def_val = self._eff_stat(mission, tgt, StatName.DEF)
        base = max(1, atk_val - def_val)
        crit = self._eff_stat(mission, atk, StatName.CRIT)
        return base * 2 if crit >= 100 else base

    # ---------- Explainable attack evaluation ----------
    def evaluate_attack(
        self, mission: Mission, attacker_id: str, target_id: str
    ) -> ActionEvaluation:
        a = mission.units[attacker_id]
        t = mission.units[target_id]

        ap_cost = 1  # attacks cost 1 AP in current engine

        atk = self._eff_stat_with_trace(mission, a, StatName.ATK)
        dfn = self._eff_stat_with_trace(mission, t, StatName.DEF)

        pen = Penetration(flat=0.0, pct=0.0)
        effective_def = max(0.0, dfn.value * (1.0 - pen.pct) - pen.flat)

        skill_ratio = 1.0
        flat_power = 0.0
        pre_mitigation = max(0.0, atk.value - effective_def)
        raw_after_def = pre_mitigation * skill_ratio + flat_power

        vulns: list[ResistEntry] = []
        atk_mult_terms: list[StatTerm] = []

        final_before_crit = raw_after_def
        # Crit expectation aligned with _compute_damage: crit only if CRIT >= 100
        crit_stat = self._eff_stat(mission, a, StatName.CRIT)
        crit_chance = 1.0 if crit_stat >= 100 else 0.0
        crit_mult = 2.0  # double damage on crit
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
            else max(
                min_cap, after_block if max_cap is None else min(after_block, max_cap)
            )
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

        # Hit chance: no explicit ACC/EVA stats in current model, so assume 100%
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

    def _skill_by_id(self, u: Unit, sid: str):
        for s in u.skills:
            if s.id == sid:
                return s
        return None

    def _attach_temp_mods(self, u: Unit, mods: list[StatModifier]) -> None:
        inj = InjuryFromMods(mods)
        u.injuries.append(inj)

    def _end_turn(self, mission: Mission) -> None:
        # cooldowns and drop mods for all units
        for u in mission.units.values():
            if not u.alive:
                continue
            # cooldowns
            for sid in list(u.skill_cooldowns.keys()):
                u.skill_cooldowns[sid] = max(0, u.skill_cooldowns.get(sid, 0) - 1)
            # drop duration-based temporary mods (stored as injuries)
            kept = []
            for inj in u.injuries:
                new_mods = []
                for m in inj.mods:
                    if m.duration_turns is None:
                        new_mods.append(m)
                    elif m.duration_turns > 1:
                        m.duration_turns -= 1
                        new_mods.append(m)
                if new_mods:
                    inj.mods = new_mods
                    kept.append(inj)
            u.injuries = kept

        # Advance initiative cursor and refill AP for the next living unit
        order = mission.initiative_order or []
        if not order:
            self._recompute_initiative_order(mission)
            order = mission.initiative_order
        if not order:
            mission.current_unit_id = None
            return

        try:
            idx = (
                order.index(mission.current_unit_id)
                if mission.current_unit_id in order
                else -1
            )
        except ValueError:
            idx = -1

        # find next living unit in order
        n = len(order)
        if n == 0:
            mission.current_unit_id = None
            return

        for step in range(1, n + 1):
            next_idx = (idx + step) % n
            candidate_id = order[next_idx]
            cu = mission.units.get(candidate_id)
            if cu and cu.alive:
                # If we wrapped around, it's a new turn
                if next_idx <= idx:
                    mission.turn += 1
                mission.current_unit_id = candidate_id
                cu.ap_left = self._eff_stat(mission, cu, StatName.AP)
                mission.side_to_move = cu.side
                break
        else:
            # nobody alive
            mission.current_unit_id = None

    def _recompute_initiative_order(self, mission: Mission) -> None:
        # order: higher INIT first; tie-breaker: Player before Enemy; then stable by name
        living: list[Unit] = [u for u in mission.units.values() if u.alive]
        living.sort(
            key=lambda u: (
                -self._eff_stat(mission, u, StatName.INIT),
                0 if u.side == Side.PLAYER else 1,
                u.name,
            )
        )
        mission.initiative_order = [u.id for u in living]
        mission.current_unit_id = mission.initiative_order[0] if living else None
        if mission.current_unit_id:
            mission.side_to_move = mission.units[mission.current_unit_id].side

    def check_victory_conditions(self, sess: TBSSession) -> MissionStatus:
        mission = sess.mission
        if mission.status != MissionStatus.IN_PROGRESS:
            return mission.status

        for goal in mission.goals:
            if goal.kind == GoalKind.ELIMINATE_ALL_ENEMIES:
                if not any(
                    u.alive and u.side == Side.ENEMY for u in mission.units.values()
                ):
                    return MissionStatus.VICTORY
            elif goal.kind == GoalKind.SURVIVE_TURNS and mission.turn >= (
                goal.survive_turns or 0
            ):
                return MissionStatus.VICTORY

        # Check for player defeat
        if not any(u.alive and u.side == Side.PLAYER for u in mission.units.values()):
            return MissionStatus.DEFEAT

        return MissionStatus.IN_PROGRESS


class InjuryFromMods(BaseModel):
    id: str = "inj.temp"
    name: str = "Temporary Effect"
    mods: list[StatModifier]

    def __init__(self, mods: list[StatModifier]):
        super().__init__(mods=mods)


def manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
