(function (global) {
  const Game = {
    mount(rootId) {
      // Styles come from index.html to keep formatting consistent across components
      document.getElementById('end-turn').onclick = global.handleEndTurn;
      document.getElementById('show-sessions').onclick = global.showSessions;
      return Game;
    },

    render(state, sid, selected, previewUnit, legalActions) {
      document.getElementById('sid').textContent = sid || '-';
      document.getElementById('turn').textContent = state ? global.turnNumber(state) ?? '-' : '-';
      document.getElementById('side').textContent = state ? global.sideToMove(state) ?? '-' : '-';
      const currentUnitId = global.currentUnitId(state);
      document.getElementById('current-unit').textContent = currentUnitId ?
        global.unitName(state.units[currentUnitId]) || 'unknown' : 'none';
      document.getElementById('ap').textContent = currentUnitId ?
        global.unitApLeft(state.units[currentUnitId]) : '-';
      document.getElementById('sel').textContent = selected && state?.units[selected] ?
        global.unitName(state.units[selected]) : 'none';
      const endTurnBtn = document.getElementById('end-turn');
      endTurnBtn.disabled = !sid;
      // Render active unit
      this.renderActiveUnit(state, legalActions);
      // Render preview unit
      this.renderPreviewUnitPanel(state, previewUnit, global.MOVE_HINTS, global.ATTACK_HINTS);
      // Initiative
      if (global.Initiative) {
        global.Initiative.render(state);
      }
    },

    renderActiveUnit(state, legalActions) {
      const wrap = document.getElementById('active-unit');
      if (!wrap) return;
      const currentUnitId = global.currentUnitId(state);
      if (!state || !currentUnitId) {
        wrap.innerHTML = 'No active unit.';
        return;
      }
      const u = state.units[currentUnitId];
      if (!u) { wrap.innerHTML = 'No active unit.'; return; }
      const base = global.unitBaseStats(u);
      const get = (k) => {
        const key = String(k);
        return (
          base[key] ??
          base[key.toLowerCase?.() || key] ??
          base[key.toUpperCase?.() || key] ??
          0
        );
      };
      const stats = {
        HP: get('HP'), AP: get('AP'), ATK: get('ATK'), DEF: get('DEF'),
        MOV: get('MOV'), RNG: get('RNG'), CRIT: get('CRIT'), INIT: get('INIT')
      };
      const items = global.unitItems(u);
      const skills = global.unitSkills(u);
      const pos = global.unitPos(u);
      const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const fmtMod = (m) => {
        if (!m) return '';
        const stat = m.stat ?? '';
        const op = m.operation ?? '';
        const val = Number(m.value) || 0;
        const sign = val >= 0 ? '+' : '-';
        const absv = Math.abs(val);
        if (op === 'ADDITIVE') return `${sign} ${absv}${stat}`;
        if (op === 'MULTIPLICATIVE') return `${sign} ${absv}%${stat}`;
        if (op === 'OVERRIDE') return `= ${absv}${stat}`;
        return `${sign} ${absv}${stat}`;
      };
      const itemTitle = (it) => {
        const name = (it && it.name) || 'Item';
        const mods = Array.isArray(it?.mods) ? it.mods.map(fmtMod).filter(Boolean) : [];
        const lines = [name];
        if (mods.length) { lines.push('Mods:'); mods.forEach(line => lines.push(` • ${line}`)); }
        return lines.join('\n');
      };
      const itemsHtml = items.length ? items.map(it => `<span class="chip" title="${esc(itemTitle(it))}">${esc((it && it.name) || 'Item')}</span>`).join('') : '<span style="color:#777;">None</span>';
      const skillsHtml = skills.length
        ? skills.map(s => {
            const ap = Number(s?.ap_cost ?? 0);
            const rng = Number(s?.range ?? 0);
            const tgt = String(s?.target || 'none');
            const tip = `${s?.name || 'Skill'}\nAP: ${ap}  RNG: ${rng}  Target: ${tgt}`;
            return `<button class="action-btn" data-skill-id="${esc(s.id)}" title="${esc(tip)}">${esc(s.name || s.id)}</button>`;
          }).join('')
        : '<span style="color:#777;">None</span>';
      const attackEntries = (legalActions || []).filter(e => e?.action?.kind === 'attack' && e.action.attacker_id === u.id);
      const attacksHtml = attackEntries.length ? attackEntries.map(e => {
        const tgt = state.units[e.action.target_id];
        const name = tgt ? `${global.unitName(tgt)} (${global.unitSide(tgt)})` : e.action.target_id;
        const sum = e.evaluation?.summary || 'Attack';
        const dmg = e.evaluation ? ` · ${Math.round(e.evaluation.hit?.result ?? 100)}% · ${e.evaluation.min_damage.toFixed(0)}–${e.evaluation.max_damage.toFixed(0)} avg ${e.evaluation.expected_damage.toFixed(1)}` : '';
        return `<button class="action-btn" data-act="attack" data-att="${e.action.attacker_id}" data-tgt="${e.action.target_id}" title="${sum}">Attack ${name}${dmg}</button>`;
      }).join('') : '<span style="color:#777;">None</span>';
      wrap.innerHTML = `
        <h3>${global.unitName(u)} <span style="font-weight:400; color:#666;">(${global.unitSide(u)})</span></h3>
        <div class="meta">Pos: ${pos[0]},${pos[1]} · AP: ${global.unitApLeft(u)}</div>
        <div class="stats-grid">
          <div><b>HP</b>: ${stats.HP}</div>
          <div><b>AP</b>: ${stats.AP}</div>
          <div><b>ATK</b>: ${stats.ATK}</div>
          <div><b>DEF</b>: ${stats.DEF}</div>
          <div><b>MOV</b>: ${stats.MOV}</div>
          <div><b>RNG</b>: ${stats.RNG}</div>
          <div><b>CRIT</b>: ${stats.CRIT}</div>
          <div><b>INIT</b>: ${stats.INIT}</div>
        </div>
        <div class="section-title">Items</div>
        <div>${itemsHtml}</div>
        <div class="section-title">Skills</div>
        <div>${skillsHtml}</div>
        <div class="section-title">Possible Attacks</div>
        <div id="attack-options">${attacksHtml}</div>
      `;
      // Wire attack buttons
      document.querySelectorAll('#attack-options button[data-act="attack"]').forEach(btn => {
        btn.onclick = async () => {
          const attacker = btn.getAttribute('data-att');
          const target = btn.getAttribute('data-tgt');
          if (!attacker || !target) return;
          await global.attemptAction({ kind: 'attack', attacker_id: attacker, target_id: target });
        };
      });
      // Wire skill buttons
      document.querySelectorAll('#active-unit .action-btn[data-skill-id]').forEach(btn => {
        btn.onclick = async () => {
          const sid = btn.getAttribute('data-skill-id');
          if (!sid) return;
          // Determine the skill from current unit
          const skill = (skills || []).find(s => s && s.id === sid);
          if (!skill) return;
          // Toggle off if already targeting this skill on this unit
          if (window.SKILL_TARGETING && window.SKILL_TARGETING.unitId === u.id && window.SKILL_TARGETING.skillId === sid) {
            window.endSkillTargeting();
            return;
          }
          const target = String(skill.target || 'none');
          // Self or none-target skills: apply immediately
          if (target === 'self' || target === 'none') {
            const action = { kind: 'use_skill', unit_id: u.id, skill_id: skill.id };
            if (target === 'self') action.target_unit_id = u.id;
            await global.attemptAction(action);
            return;
          }
          // Otherwise enter targeting mode and highlight legal tiles/units
          await global.startSkillTargeting(u.id, skill.id);
        };
      });
    },

    renderPreviewUnitPanel(state, previewUnit, moveHints, attackHints) {
      const wrap = document.getElementById('preview-unit');
      if (!wrap) return;
      if (!state) { wrap.innerHTML = 'No data.'; return; }
      const uid = previewUnit || null;
      if (!uid || !state.units[uid]) {
        wrap.innerHTML = 'Click any unit to preview its MOV/RNG and possible moves/attacks.';
        return;
      }
      const u = state.units[uid];
      const base = global.unitBaseStats(u);
      const get = (k) => {
        const key = String(k);
        return (
          base[key] ??
          base[key.toLowerCase?.() || key] ??
          base[key.toUpperCase?.() || key] ??
          0
        );
      };
      const MOV = get('MOV');
      const RNG = get('RNG');
      const AP = global.unitApLeft(u) || get('AP') || 0;
      const pos = global.unitPos(u);
      const moveCount = moveHints.size;
      const atkCount = attackHints.size;
      const mode = (global.currentUnitId(state) === uid) ? 'active (precise)' : 'preview (estimate)';
      wrap.innerHTML = `
        <h3>Preview: ${global.unitName(u)} <span style="font-weight:400; color:#666;">(${global.unitSide(u)})</span></h3>
        <div class="meta">Pos: ${pos[0]},${pos[1]} · Mode: ${mode}</div>
        <div class="stats-grid">
          <div><b>AP</b>: ${AP}</div>
          <div><b>MOV</b>: ${MOV}</div>
          <div><b>RNG</b>: ${RNG}</div>
          <div><b>Hints</b>: ${moveCount} moves, ${atkCount} targets</div>
        </div>
      `;
    }
  };

  global.Game = Game;
})(window);
