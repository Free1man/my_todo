(function (global) {
  const STYLE_ID = 'game-styles';

  const CSS = `
    /* Game component styles */
    .game-panel {
      margin: 20px;
    }
    .status {
      background: #f5f5f5;
      padding: 8px;
      border-radius: 4px;
      font-size: 14px;
    }
    .unit-info {
      background: #e8f5e8;
      padding: 8px;
      border-radius: 4px;
    }
    .board-row {
      display: flex;
      align-items: flex-start;
      gap: 16px;
    }
    .sidebar {
      flex: 0 0 300px;
      width: 300px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .unit-card {
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      padding: 8px;
      min-width: 280px;
      font-size: 12px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    .unit-card h3 {
      margin: 0 0 4px;
      font-size: 14px;
    }
    .unit-card .meta {
      color: #555;
      font-size: 11px;
      margin-bottom: 6px;
    }
    .unit-card .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, auto);
      gap: 4px 10px;
      margin-bottom: 6px;
    }
    .unit-card .section-title {
      font-weight: 600;
      margin: 6px 0 4px;
      color: #444;
      font-size: 12px;
    }
    .chip {
      display: inline-block;
      padding: 2px 6px;
      border: 1px solid #e0e0e0;
      border-radius: 10px;
      background: #f5f7fa;
      margin: 2px 4px 0 0;
      font-size: 11px;
      white-space: nowrap;
    }
  `;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  const Game = {
    mount(rootId) {
      ensureStyles();
      // Assume HTML is already in place
      document.getElementById('end-turn').onclick = global.handleEndTurn;
      document.getElementById('show-sessions').onclick = global.showSessions;
      return Game;
    },

    render(state, sid, selected, previewUnit, legalActions) {
      document.getElementById('sid').textContent = sid || '-';
      document.getElementById('turn').textContent = state ? state.turn : '-';
      document.getElementById('side').textContent = state ? state.side_to_move : '-';
      document.getElementById('current-unit').textContent = state?.current_unit_id ?
        state.units[state.current_unit_id]?.name || 'unknown' : 'none';
      document.getElementById('ap').textContent = state?.current_unit_id ?
        state.units[state.current_unit_id]?.ap_left || 0 : '-';
      document.getElementById('sel').textContent = selected && state?.units[selected] ?
        state.units[selected].name : 'none';
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
      if (!state || !state.current_unit_id) {
        wrap.innerHTML = 'No active unit.';
        return;
      }
      const u = state.units[state.current_unit_id];
      if (!u) { wrap.innerHTML = 'No active unit.'; return; }
      const base = (u.stats && u.stats.base) || {};
      const get = (k) => base[k] ?? base[String(k)] ?? 0;
      const stats = {
        HP: get('HP'), AP: get('AP'), ATK: get('ATK'), DEF: get('DEF'),
        MOV: get('MOV'), RNG: get('RNG'), CRIT: get('CRIT'), INIT: get('INIT')
      };
      const items = Array.isArray(u.items) ? u.items : [];
      const skills = Array.isArray(u.skills) ? u.skills : [];
      const pos = Array.isArray(u.pos) ? u.pos : (u.pos || [0, 0]);
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
      const skillsHtml = skills.length ? skills.map(s => `<span class="chip" title="${(s && s.name) || 'Skill'}">${(s && s.name) || 'Skill'}</span>`).join('') : '<span style="color:#777;">None</span>';
      const attackEntries = (legalActions || []).filter(e => e?.action?.kind === 'attack' && e.action.attacker_id === u.id);
      const attacksHtml = attackEntries.length ? attackEntries.map(e => {
        const tgt = state.units[e.action.target_id];
        const name = tgt ? `${tgt.name} (${tgt.side})` : e.action.target_id;
        const sum = e.evaluation?.summary || 'Attack';
        const dmg = e.evaluation ? ` · ${Math.round(e.evaluation.hit?.result ?? 100)}% · ${e.evaluation.min_damage.toFixed(0)}–${e.evaluation.max_damage.toFixed(0)} avg ${e.evaluation.expected_damage.toFixed(1)}` : '';
        return `<button class="action-btn" data-act="attack" data-att="${e.action.attacker_id}" data-tgt="${e.action.target_id}" title="${sum}">Attack ${name}${dmg}</button>`;
      }).join('') : '<span style="color:#777;">None</span>';
      wrap.innerHTML = `
        <h3>${u.name} <span style="font-weight:400; color:#666;">(${u.side})</span></h3>
        <div class="meta">Pos: ${pos[0]},${pos[1]} · AP: ${u.ap_left ?? 0}</div>
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
      const base = (u.stats && u.stats.base) || {};
      const get = (k) => base[k] ?? base[String(k)] ?? 0;
      const MOV = get('MOV');
      const RNG = get('RNG');
      const AP = u.ap_left ?? get('AP') ?? 0;
      const pos = Array.isArray(u.pos) ? u.pos : (u.pos || [0, 0]);
      const moveCount = moveHints.size;
      const atkCount = attackHints.size;
      const mode = (state.current_unit_id === uid) ? 'active (precise)' : 'preview (estimate)';
      wrap.innerHTML = `
        <h3>Preview: ${u.name} <span style="font-weight:400; color:#666;">(${u.side})</span></h3>
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
