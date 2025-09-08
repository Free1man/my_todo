(function (global) {
  // Utils for common functions
  global.BUSY = false;
  global.api = async function(path, opts = {}) {
    const r = await fetch(path, { headers: { 'content-type': 'application/json' }, ...opts });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  };

  global.log = function(msg, level) {
    if (global.Log) {
      global.Log.addEntry(msg, level);
    } else {
      console.log(msg);
    }
  };

  global.getUnit = (id) => (global.STATE && id ? global.STATE.units[id] : null);
  global.tileKey = (x, y) => `${x},${y}`;
  global.manh = (a, b) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
  global.inBounds = (x, y) => global.STATE && 0 <= x && x < global.STATE.map.width && 0 <= y && y < global.STATE.map.height;
  global.terrainAt = (x, y) => (global.STATE.map.tiles[y][x]?.terrain || 'plain').toLowerCase();
  global.isWalkable = (x, y) => { const t = global.terrainAt(x, y); return !(t === 'blocked' || t === 'water'); };
  global.isOccupied = (x, y) => Object.values(global.STATE.units).some(u => u.alive && u.pos[0] === x && u.pos[1] === y);
  global.neighbors = (x, y) => [[x+1,y],[x-1,y],[x,y+1],[x,y-1]].filter(([nx, ny]) => global.inBounds(nx, ny));
  global.clearHints = () => { global.MOVE_HINTS.clear(); global.ATTACK_HINTS.clear(); };

  // Batch UI renders into the next animation frame
  global._renderScheduled = false;
  global.requestRender = function() {
    if (global._renderScheduled) return;
    global._renderScheduled = true;
    requestAnimationFrame(() => {
      global._renderScheduled = false;
      if (global.Game) {
        global.Game.render(global.STATE, global.SID, global.SELECTED, global.PREVIEW_UNIT, global.LEGAL_ACTIONS);
      }
      if (global.Grid) {
        global.Grid.render(global.STATE, global.SELECTED, global.PREVIEW_UNIT, global.MOVE_HINTS, global.ATTACK_HINTS);
      }
    });
  };

  global.showGame = function() {
    document.getElementById('sessions').style.display = 'none';
    document.getElementById('create').style.display = 'none';
    document.getElementById('game').style.display = '';
  };

  global.showSessions = function() {
    document.getElementById('game').style.display = 'none';
    document.getElementById('create').style.display = 'none';
    document.getElementById('sessions').style.display = '';
  };

  global.showCreate = function() {
    document.getElementById('sessions').style.display = 'none';
    document.getElementById('game').style.display = 'none';
    document.getElementById('create').style.display = '';
  };

  global.handleNewGame = async function() {
    try {
      global.log('Creating new session...');
      const res = await global.api('/sessions', { method: 'POST', body: JSON.stringify({}) });
      global.SID = res.id;
      global.STATE = res.mission;
      global.SELECTED = global.STATE.current_unit_id || null;
      global.PREVIEW_UNIT = null;
      global.LEGAL_ACTIONS = [];
      global.log(`Session ${global.SID} created`);
        global.updateUI();
        await global.fetchLegalAndComputeHints();
        global.render();
        global.showGame();
        global.Sessions.refresh();
    } catch (e) {
      global.log(`Error: ${e.message}`, 'error');
    }
  };

  global.handleCreateSession = async function() {
    global.CreateSession.prepare();
    global.showCreate();
  };

  global.handleEndTurn = async function() {
    if (global.BUSY || !global.SID) return;
    global.BUSY = true;
    const action = { kind: 'end_turn' };
    try {
      const res = await global.api(`/sessions/${global.SID}/action`, { method: 'POST', body: JSON.stringify({ action }) });
      global.STATE = res.session.mission;
      global.SELECTED = global.STATE.current_unit_id || null;
      global.PREVIEW_UNIT = null;
      global.LEGAL_ACTIONS = [];
      global.log(`Turn ended: ${res.explanation}`, 'success');
      await global.fetchLegalAndComputeHints();
      global.updateUI();
    } finally {
      global.BUSY = false;
    }
  };

  global.loadSession = async function(id) {
    try {
      const sess = await global.api(`/sessions/${id}`);
      global.SID = sess.id;
      global.STATE = sess.mission;
      global.SELECTED = sess.mission.current_unit_id || null;
      global.PREVIEW_UNIT = null;
      global.LEGAL_ACTIONS = [];
      await global.fetchLegalAndComputeHints();
      global.log(`Loaded session ${global.SID}`);
  global.updateUI();
      global.showGame();
    } catch (e) {
      global.log(`Error loading session: ${e.message}`, 'error');
    }
  };

  global.attemptAction = async function(action) {
    if (!global.SID || global.BUSY) return false;
    global.BUSY = true;
    try {
      const res = await global.api(`/sessions/${global.SID}/action`, { method: 'POST', body: JSON.stringify({ action }) });
      global.STATE = res.session.mission;
      global.SELECTED = global.STATE.current_unit_id || null;
      global.PREVIEW_UNIT = null;
      global.log(`Action applied: ${res.explanation}`, 'success');
      await global.fetchLegalAndComputeHints();
      global.updateUI();
      return true;
    } catch (e) {
      global.log(`Action failed: ${e.message}`, 'error');
      global.MOVE_HINTS.clear();
      global.ATTACK_HINTS.clear();
      global.updateUI();
      return false;
    } finally {
      global.BUSY = false;
    }
  };

  global.fetchLegalAndComputeHints = async function() {
    global.MOVE_HINTS.clear();
    global.ATTACK_HINTS.clear();
    if (!global.SID || !global.STATE) return;

    const targetId = global.PREVIEW_UNIT || global.SELECTED || global.STATE.current_unit_id;
    if (!targetId) return;
    const sel = global.STATE.units[targetId];
    if (!sel) return;

    if (global.STATE.current_unit_id === targetId) {
      try {
        const res = await global.api(`/sessions/${global.SID}/legal_actions?explain=true`);
        global.LEGAL_ACTIONS = res.actions || [];
      } catch (e) {
        global.log(`Error fetching legal actions: ${e.message}`, 'error');
        return;
      }
      for (const entry of global.LEGAL_ACTIONS) {
        const a = entry.action || entry;
        if (a.kind === 'move' && a.unit_id === targetId && Array.isArray(a.to)) {
          global.MOVE_HINTS.add(`${a.to[0]},${a.to[1]}`);
        }
        if (a.kind === 'attack' && a.attacker_id === targetId) {
          const tgt = global.STATE.units[a.target_id];
          if (tgt && tgt.alive && tgt.side !== sel.side) {
            global.ATTACK_HINTS.set(`${tgt.pos[0]},${tgt.pos[1]}`, tgt.id);
          }
        }
      }
  return;
    }

    const base = (sel.stats && sel.stats.base) || {};
    const MOV = Number(
      base.MOV ?? base['MOV'] ?? base.mov ?? base['mov'] ?? 0
    );
    const RNG = Number(
      base.RNG ?? base['RNG'] ?? base.rng ?? base['rng'] ?? 0
    );

    if (MOV > 0) {
      const start = [sel.pos[0], sel.pos[1]];
      const queue = [[start, 0]];
      const seen = new Set([`${start[0]},${start[1]}`]);
      while (queue.length) {
        const [[x, y], d] = queue.shift();
        if (d >= MOV) continue;
        for (const [nx, ny] of global.neighbors(x, y)) {
          const key = `${nx},${ny}`;
          if (seen.has(key)) continue;
          if (!global.isWalkable(nx, ny)) continue;
          if (global.isOccupied(nx, ny)) continue;
          seen.add(key);
          global.MOVE_HINTS.add(key);
          queue.push([[nx, ny], d+1]);
        }
      }
    }

    if (RNG > 0) {
      for (const other of Object.values(global.STATE.units)) {
        if (!other.alive || other.id === sel.id) continue;
        if (other.side === sel.side) continue;
        if (global.manh(sel.pos, other.pos) <= RNG) {
          global.ATTACK_HINTS.set(`${other.pos[0]},${other.pos[1]}`, other.id);
        }
      }
    }
  // Preview panel is rendered as part of Game.render; no direct DOM writes here
  };

  global.updateUI = function() {
  global.requestRender();
  };

  global.render = function() {
  global.requestRender();
  };

  // --- Skill targeting helpers ---
  global.SKILL_TARGETING = null; // { unitId, skillId }
  global.SKILL_TARGETS = null;   // { tiles: Set<string>, units: Set<string> }

  global.startSkillTargeting = async function(unitId, skillId) {
    if (!global.SID || !global.STATE) return;
    global.SKILL_TARGETING = { unitId, skillId };
    const tiles = new Set();
    const units = new Set();
  // Resolve skill details for fallback targeting ranges
  const unit = global.STATE.units[unitId];
  const skill = unit && Array.isArray(unit.skills) ? unit.skills.find(s => s && s.id === skillId) : null;
  const range = Number(skill?.range ?? 0);
  const targetKind = String(skill?.target || 'none');
    try {
      const res = await global.api(`/sessions/${global.SID}/legal_actions?explain=true`);
      const actions = Array.isArray(res?.actions) ? res.actions : [];
      for (const entry of actions) {
        const a = entry.action || entry;
        if (a.kind !== 'use_skill') continue;
        if (a.unit_id !== unitId) continue;
        if (a.skill_id !== skillId) continue;
        if (Array.isArray(a.target_tile)) {
          tiles.add(`${a.target_tile[0]},${a.target_tile[1]}`);
        }
        if (a.target_unit_id) {
          const u = global.STATE.units[a.target_unit_id];
          if (u && Array.isArray(u.pos)) {
            units.add(a.target_unit_id);
            tiles.add(`${u.pos[0]},${u.pos[1]}`);
          }
        }
      }
      // Fallback for TILE-targeted skills: allow any in-range tile (including empty)
      if (targetKind === 'tile') {
        const pos = Array.isArray(unit?.pos) ? unit.pos : [0, 0];
        const H = global.STATE.map?.height ?? 0;
        const W = global.STATE.map?.width ?? 0;
        if (range <= 0) {
          tiles.add(`${pos[0]},${pos[1]}`);
        } else {
          for (let y = 0; y < H; y++) {
            for (let x = 0; x < W; x++) {
              const d = Math.abs(x - pos[0]) + Math.abs(y - pos[1]);
              if (d <= range) tiles.add(`${x},${y}`);
            }
          }
        }
      }
      global.SKILL_TARGETS = { tiles, units };
      global.log(`Targeting ${skillId}: ${units.size} unit(s), ${tiles.size} tile(s)`);
    } catch (e) {
      global.log(`Error loading skill targets: ${e.message}`, 'error');
      global.SKILL_TARGETING = null;
      global.SKILL_TARGETS = null;
    }
    global.requestRender();
  };

  global.endSkillTargeting = function() {
    global.SKILL_TARGETING = null;
    global.SKILL_TARGETS = null;
    global.requestRender();
  };

  // Right-click (context menu) cancels targeting if active, before other handlers
  document.addEventListener(
    'contextmenu',
    (e) => {
      if (window.SKILL_TARGETING) {
        e.preventDefault();
        e.stopPropagation();
        if (e.stopImmediatePropagation) e.stopImmediatePropagation();
        window.endSkillTargeting();
      }
    },
    true // capture to intercept before element handlers like unit preview
  );
})(window);
