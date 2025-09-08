(function (global) {
  const Log = {
    mount(rootId) {
      // Styles come from index.html to keep formatting consistent across components
      this.rootId = rootId;
      return Log;
    },

    // Client-generated log was removed; use server-side events only
  };

  // Server-side action log helpers
  Log.fetchActionLog = async function(sessionId, limit = 50) {
    if (!sessionId) return [];
    try {
      const res = await fetch(`/sessions/${encodeURIComponent(sessionId)}/log?limit=${limit}`);
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data?.entries) ? data.entries : [];
    } catch {
      return [];
    }
  };

  Log.renderActionLog = function(container, entries) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = '';
    const list = Array.isArray(entries) ? entries : [];
    for (const e of list) {
      const wrap = document.createElement('div');
      wrap.className = 'log-entry';
      const ts = e?.ts ? new Date(e.ts).toLocaleTimeString() : '';
      const kind = e?.action?.kind || '?';
      const actor = e?.actor_unit_id || '?';
      const result = e?.result || 'applied';
      // Single-line summary
      wrap.textContent = `[${ts}] ${kind} by ${actor} → ${result}`;
      // Hover tooltip with more info (action model + attack_eval/message)
      const details = {
        action: e?.action || null,
        message: e?.message || null,
        attack_eval: e?.attack_eval || null,
      };
      wrap.title = JSON.stringify(details, null, 2);
      el.appendChild(wrap);
    }
  };

  global.Log = Log;
})(window);
