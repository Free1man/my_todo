(function (global) {
  const STYLE_ID = 'sessions-styles';

  const CSS = `
    /* Sessions component styles */
    .sessions-panel {
      margin: 20px;
    }
    .sessions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 10px;
    }
    .session-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 6px 8px;
      border: 1px solid #eee;
      border-radius: 4px;
      cursor: pointer;
    }
    .session-info {
      flex: 1;
    }
    .session-btn {
      padding: 4px 8px;
      font-size: 12px;
    }
  `;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  const Sessions = {
    mount(rootId) {
      ensureStyles();
      // Assume HTML is already in place, just wire events
      document.getElementById('new').onclick = global.handleNewGame;
      document.getElementById('create-session').onclick = global.handleCreateSession;
      document.getElementById('refresh-sessions').onclick = () => this.refresh();
      return Sessions;
    },

    async refresh() {
      const container = document.getElementById('sessions-list');
      if (!container) return;
      container.innerHTML = '';
      try {
        const sessions = await global.api('/sessions');
        if (!Array.isArray(sessions) || sessions.length === 0) {
          const empty = document.createElement('div');
          empty.textContent = 'No sessions yet.';
          empty.style.color = '#666';
          container.appendChild(empty);
          return;
        }
        sessions.forEach(s => {
          const row = document.createElement('div');
          row.className = 'session-row';
          const info = document.createElement('div');
          info.className = 'session-info';
          const m = s.mission || {};
          const unitsCount = m.units ? Object.keys(m.units).length : 0;
          info.textContent = `${s.id} — Turn ${m.turn ?? '-'} | Side ${m.side_to_move ?? '-'} | Units ${unitsCount}`;
          const btn = document.createElement('button');
          btn.className = 'session-btn action-btn';
          btn.textContent = 'Continue';
          btn.onclick = (ev) => {
            ev.stopPropagation();
            global.loadSession(s.id);
          };
          row.onclick = () => global.loadSession(s.id);
          row.appendChild(info);
          row.appendChild(btn);
          container.appendChild(row);
        });
      } catch (e) {
        global.log(`Error fetching sessions: ${e.message}`, 'error');
      }
    },

    render(state, sid) {
      // Update any dynamic parts if needed
      // For now, sessions are refreshed separately
    }
  };

  global.Sessions = Sessions;
})(window);
