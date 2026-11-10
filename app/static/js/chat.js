(function () {
  const box = document.getElementById('msgs'), form = document.getElementById('composer'), input = document.getElementById('msg');
  const history = [];
  const esc = s => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const md = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');

  function add(role, html, cls) {
    const el = document.createElement('div');
    el.className = 'bubble ' + role + (cls ? ' ' + cls : '');
    el.innerHTML = html; box.appendChild(el); box.scrollTop = box.scrollHeight; return el;
  }

  async function send(text) {
    add('me', esc(text)); input.value = '';
    const wait = add('bot', 'Je réfléchis…', 'typing');
    try {
      const r = await api('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, history }) });
      wait.remove(); add('bot', md(r.answer || r.error || 'Pas de réponse.'));
      history.push({ role: 'user', content: text }, { role: 'assistant', content: r.answer || '' });
    } catch (e) { wait.remove(); add('bot', 'Une erreur est survenue. Réessaie dans un instant.'); }
  }

  form.addEventListener('submit', e => { e.preventDefault(); const t = input.value.trim(); if (t) send(t); });
  document.querySelectorAll('[data-q]').forEach(b => b.addEventListener('click', () => send(b.dataset.q)));
})();
