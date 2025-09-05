(function (global) {
  const STYLE_ID = 'grid-styles';

  const CSS = `
    /* Grid component styles */
    #grid {
      display: grid;
      grid-auto-rows: 32px;
      grid-auto-columns: 32px;
      gap: 1px;
      margin: 10px 0;
      border: 1px solid #ccc;
    }
    .tile {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid #ddd;
      font-size: 10px;
      position: relative;
    }
    .water { background: #7ec8e3; }
    .blocked { background: #666; color: #fff; }
    .plain { background: #f5f5f5; }
    .forest { background: #8bc34a; }
    .hill { background: #ff9800; }
    .tile.selected::before {
      content: "";
      position: absolute;
      inset: 0;
      border: 3px solid #00bcd4;
      border-radius: 0;
      pointer-events: none;
      z-index: 3;
      box-shadow: 0 0 2px rgba(0, 188, 212, 0.5) inset;
    }
    .tile.current::after {
      content: "★";
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 14px;
      line-height: 1;
      color: #ffca28;
      text-shadow: 0 1px 1px rgba(0,0,0,0.35);
      pointer-events: none;
      z-index: 4;
    }
    .tile.current { box-shadow: inset 0 0 0 2px #2196f3; }
    .u {
      border-radius: 4px;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 11px;
      position: relative;
      border: 1px solid rgba(0, 0, 0, 0.08);
      z-index: 1;
    }
    .player { background: #4caf50; color: #fff; }
    .enemy { background: #7e57c2; color: #fff; }
    .neutral { background: #9e9e9e; color: #fff; }
    .dead { opacity: 0.3; }
    .tile.move { box-shadow: inset 0 0 0 2px rgba(76, 175, 80, 0.45); }
    .tile.move::after {
      content: "";
      position: absolute;
      inset: 0;
      background: rgba(76, 175, 80, 0.18);
      pointer-events: none;
    }
    .tile .ring {
      position: absolute;
      width: 26px;
      height: 26px;
      border: 3px solid #ef5350;
      border-radius: 50%;
      pointer-events: none;
      box-shadow: 0 0 6px rgba(239, 83, 80, 0.6);
      z-index: 2;
    }
  `;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  const Grid = {
    mount(rootId) {
      ensureStyles();
      // Assume #grid is already in place
      return Grid;
    },

    render(state, selected, previewUnit, moveHints, attackHints) {
      const gridEl = document.getElementById('grid');
      if (!gridEl || !state) return;
      const map = state.map;
      if (!map) return;
      gridEl.style.gridTemplateColumns = `repeat(${map.width}, 32px)`;
      gridEl.style.gridTemplateRows = `repeat(${map.height}, 32px)`;
      gridEl.innerHTML = '';
      for (let y = 0; y < map.height; y++) {
        for (let x = 0; x < map.width; x++) {
          const tile = document.createElement('div');
          tile.className = 'tile ' + (map.tiles[y][x]?.terrain || 'plain').toLowerCase();
          tile.dataset.x = x;
          tile.dataset.y = y;
          // Units
          const unit = Object.values(state.units).find(u => u.alive && u.pos[0] === x && u.pos[1] === y);
          if (unit) {
            const dot = document.createElement('div');
            dot.className = 'u ' + String(unit.side || '').toLowerCase() + (unit.alive ? '' : ' dead');
            const base = (unit.stats && unit.stats.base) || {};
            const hp = (base.hp ?? base.HP ?? base['hp'] ?? 0);
            const ap = (unit.ap_left ?? 0);
            dot.innerHTML = `<div style="line-height:1.05; text-align:center; font-size:10px;">
      <div>hp: ${hp}</div>
      <div>ap: ${ap}</div>
    </div>`;
            dot.onclick = async (e) => {
              if (unit.side !== (state.current_unit_id ? state.units[state.current_unit_id]?.side : null)) {
                const acting = state.units[state.current_unit_id];
                if (acting) {
                  const action = { kind: 'attack', attacker_id: acting.id, target_id: unit.id };
                  global.attemptAction(action);
                }
              } else {
                global.SELECTED = unit.id;
                global.PREVIEW_UNIT = null;
                await global.fetchLegalAndComputeHints();
                global.updateUI();
                global.render();
              }
            };
            dot.oncontextmenu = async (e) => {
              e.preventDefault();
              global.PREVIEW_UNIT = unit.id;
              await global.fetchLegalAndComputeHints();
              global.updateUI();
              global.render();
            };
            tile.appendChild(dot);
          }
          // Hints
          if (moveHints.has(`${x},${y}`)) {
            tile.classList.add('move');
          }
          if (attackHints.has(`${x},${y}`)) {
            const ring = document.createElement('div');
            ring.className = 'ring';
            tile.appendChild(ring);
          }
          // Selection
          if (selected && state.units[selected] && state.units[selected].pos[0] === x && state.units[selected].pos[1] === y) {
            tile.classList.add('selected');
          }
          if (state.current_unit_id && state.units[state.current_unit_id] && state.units[state.current_unit_id].pos[0] === x && state.units[state.current_unit_id].pos[1] === y) {
            tile.classList.add('current');
          }
          // Click for move
          tile.onclick = () => {
            if (!global.SID || !selected) return;
            const to = [x, y];
            const selectedUnit = state.units[selected];
            const isCurrentSel = state.current_unit_id === selectedUnit.id;
            const targetUnit = Object.values(state.units).find(u => u.alive && u.pos[0] === x && u.pos[1] === y);
            if (!isCurrentSel) return;
            let action;
            if (targetUnit && targetUnit.side !== selectedUnit.side) {
              global.log(`Attempting to attack ${targetUnit.name}...`);
              action = { kind: 'attack', attacker_id: selectedUnit.id, target_id: targetUnit.id };
            } else {
              action = { kind: 'move', unit_id: selectedUnit.id, to };
            }
            global.attemptAction(action);
          };
          gridEl.appendChild(tile);
        }
      }
    }
  };

  global.Grid = Grid;
})(window);
