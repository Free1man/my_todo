(function (global) {
  const STYLE_ID = 'create-session-styles';

  const CSS = `
    /* Create Session component styles */
    .create-panel {
      margin: 20px;
    }
    .create-editor {
      width: 100%;
      min-height: 360px;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
    }
    .create-json {
      display: none;
      width: 100%;
      min-height: 360px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Courier New', monospace;
      font-size: 12px;
      padding: 8px;
    }
    .editor-controls {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      margin: 8px 0;
    }
  `;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  let CREATE_EDITOR = null;

  const CreateSession = {
    mount(rootId) {
      ensureStyles();
      // Assume HTML is already in place
      document.getElementById('cancel-create').onclick = global.showSessions;
      document.getElementById('submit-session').onclick = () => this.submit();
      document.getElementById('mode-tree').onchange = () => this.switchMode('tree');
      document.getElementById('mode-text').onchange = () => this.switchMode('text');
      document.getElementById('expand-all').onclick = () => { if (CREATE_EDITOR) CREATE_EDITOR.expandAll(); };
      document.getElementById('collapse-all').onclick = () => { if (CREATE_EDITOR) CREATE_EDITOR.collapseAll(); };
      return CreateSession;
    },

    async prepare() {
      try {
        const info = await global.api('/info');
        let example = (info.requests && info.requests.create_session && info.requests.create_session.example)
          ? info.requests.create_session.example
          : { mission: info?.models?.mission?.example };
        if (!example || !example.mission) {
          example = { mission: {} };
          global.log('Could not find example mission in /info; starting with empty object', 'warn');
        }
        const ta = document.getElementById('create-json');
        const editorEl = document.getElementById('create-editor');
        ta.value = JSON.stringify(example, null, 2);
        document.getElementById('create-status').style.display = 'none';
        this.switchMode('tree');
      } catch (e) {
        global.log(`Error preparing create session: ${e.message}`, 'error');
      }
    },

    switchMode(mode) {
      const ta = document.getElementById('create-json');
      const editorEl = document.getElementById('create-editor');
      if (mode === 'text') {
        if (CREATE_EDITOR) {
          ta.value = JSON.stringify(CREATE_EDITOR.get(), null, 2);
        }
        ta.style.display = '';
        editorEl.style.display = 'none';
      } else {
        ta.style.display = 'none';
        editorEl.style.display = '';
        if (!CREATE_EDITOR) {
          CREATE_EDITOR = new JSONEditor(editorEl, { mode: 'tree' });
        }
        try {
          CREATE_EDITOR.set(JSON.parse(ta.value));
        } catch (e) {
          global.log('Invalid JSON in textarea', 'error');
        }
      }
    },

    async submit() {
      const status = document.getElementById('create-status');
      status.style.display = '';
      status.textContent = 'Submitting...';
      status.classList.remove('error');
      try {
        let body;
        if (CREATE_EDITOR && document.getElementById('mode-tree').checked) {
          body = CREATE_EDITOR.get();
        } else {
          body = JSON.parse(document.getElementById('create-json').value);
        }
        const res = await global.api('/sessions', { method: 'POST', body: JSON.stringify(body) });
        global.SID = res.id;
        global.STATE = res.mission;
        global.SELECTED = global.STATE.current_unit_id || null;
        global.PREVIEW_UNIT = null;
        global.LEGAL_ACTIONS = [];
        global.log(`Custom session ${global.SID} created`);
  await global.fetchLegalAndComputeHints();
  global.updateUI();
  global.render();
        global.showGame();
        global.Sessions.refresh();
        status.textContent = 'Created successfully!';
      } catch (e) {
        status.textContent = 'Error: ' + e.message;
        status.classList.add('error');
      }
    },

    render(state, sid) {
      // No dynamic render needed
    }
  };

  global.CreateSession = CreateSession;
})(window);
