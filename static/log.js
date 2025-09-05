(function (global) {
  const Log = {
    mount(rootId) {
      // Styles come from index.html to keep formatting consistent across components
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
