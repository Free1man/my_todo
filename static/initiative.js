(function (global) {
  const STYLE_ID = 'initiative-styles';

  const CSS = `
    /* Initiative component styles */
    .queue-container {
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      background: #fff;
      margin-bottom: 10px;
      width: 100%;
    }
    .queue-container .queue-header {
      padding: 6px 8px;
      font-weight: 600;
      font-size: 12px;
      color: #333;
      border-bottom: 1px solid #eee;
    }
    .queue {
      display: grid;
      grid-template-columns: repeat(auto-fill, 70px);
      gap: 6px;
      padding: 8px;
      justify-content: start; /* left align when wrapping */
      align-items: start;
    }
    .queue-item {
      width: 70px;
      height: 35px;
      box-sizing: border-box;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      background: #fafafa;
      padding: 3px 5px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      line-height: 1.15;
      position: relative;
    }
    .queue-item .q-name { font-weight: 600; font-size: 8px; color: #222; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .queue-item .q-footer { display: flex; align-items: center; gap: 4px; margin-top: 1px; }
    .queue-item .q-side { color: #666; font-size: 7px; text-transform: lowercase; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .queue-item .q-init {
      margin-left: auto;
      color: #333;
      background: #f0f0f0;
      border: 1px solid #e0e0e0;
      border-radius: 10px;
      padding: 0 5px;
      font-size: 8px;
      line-height: 1.2;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }
    .queue-item.current { border-color: #2196f3; box-shadow: 0 0 0 2px #e3f2fd inset; }
    .queue-item.dead { opacity: 0.55; }
    .queue-item.side-PLAYER { border-left: 4px solid #4caf50; }
    .queue-item.side-ENEMY { border-left: 4px solid #7e57c2; }
    .queue-item.side-NEUTRAL { border-left: 4px solid #9e9e9e; }
  `;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  const Initiative = {
    mount(rootId) {
      ensureStyles();
      const root = typeof rootId === 'string' ? document.getElementById(rootId) : rootId;
      if (!root) return;
      root.innerHTML = `
        <div class="queue-container">
          <div class="queue-header">Initiative</div>
          <div id="init-queue" class="queue"></div>
        </div>
      `;
      return Initiative;
    },

    render(state) {
      const wrap = document.getElementById('init-queue');
      if (!wrap) return;
      wrap.innerHTML = '';
      if (!state) return;
      const order = Array.isArray(state.initiative_order) ? state.initiative_order : [];
      if (!order.length) return;
      order.forEach(uid => {
        const u = state.units[uid];
        if (!u) return;
        const base = (u.stats && u.stats.base) || {};
        const init = base.INIT ?? base['INIT'] ?? 0;
        const div = document.createElement('div');
        div.className = 'queue-item side-' + u.side + (uid === state.current_unit_id ? ' current' : '') + (!u.alive ? ' dead' : '');
        const nameShort = (u.name || '').slice(0, 10);
        const sideShort = (u.side || '').toLowerCase().slice(0, 10);
        div.innerHTML = `
          <div class="q-name" title="${u.name}">${nameShort}</div>
          <div class="q-footer">
            <div class="q-side" title="${u.side.toLowerCase()}">${sideShort}</div>
            <div class="q-init">${init}</div>
          </div>
        `;
        div.title = `Unit: ${u.name} (${u.side})\nINIT: ${init}`;
        wrap.appendChild(div);
      });
    }
  };

  global.Initiative = Initiative;
})(window);
