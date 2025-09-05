(function (global) {
  const Grid = {
    mount(rootId) {
      // Styles come from index.html to keep formatting consistent across components
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
