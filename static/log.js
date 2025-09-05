(function (global) {
  const STYLE_ID = 'log-styles';

  const CSS = `
    /* Log component styles */
    .log {
      background: #f9f9f9;
      border: 1px solid #ddd;
      padding: 8px;
      height: 160px;
      overflow-y: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 12px;
      text-align: left;
    }
    .log-entry {
      padding: 6px 8px;
      border-bottom: 1px dashed #e0e0e0;
      border-left: 3px solid transparent;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .log-entry:last-child { border-bottom: none; }
    .log-entry.success {
      background: #e8f5e9;
      color: #1b5e20;
      border-left-color: #2e7d32;
    }
    .log-entry.warn {
      background: #fff8e1;
      color: #5d4037;
      border-left-color: #f9a825;
    }
    .log-entry.error {
      background: #fde7e7;
      color: #b71c1c;
      border-left-color: #d32f2f;
    }
  `;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  const Log = {
    mount(rootId) {
      ensureStyles();
      // Assume #log is already in place
      return Log;
    },

    addEntry(msg, level) {
      const p = document.getElementById('log');
      if (!p) return;
      const time = new Date().toLocaleTimeString();
      let cls = level || 'info';
      const m = String(msg).toLowerCase();
      const negatives = ['error', 'not legal', 'failed', 'invalid', 'cannot', "can't", 'out of range', 'unknown', 'missing'];
      if (!level && negatives.some(k => m.includes(k))) cls = 'error';
      const div = document.createElement('div');
      div.className = 'log-entry' + (cls && cls !== 'info' ? ' ' + cls : '');
      div.textContent = `[${time}] ${msg}`;
      if (p.firstChild) p.insertBefore(div, p.firstChild); else p.appendChild(div);
    }
  };

  global.Log = Log;
})(window);
