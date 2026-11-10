(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  window.toast = function (msg) {
    const box = $('#toasts');
    if (!box) return;
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => el.remove(), 3800);
  };

  window.api = async function (url, opts) {
    const res = await fetch(url, opts);
    if (res.status === 401) { location.href = '/login'; throw new Error('401'); }
    return res.json();
  };

  // Couleur des scores (vert si >= 60)
  $$('.score[data-s]').forEach(el => { if (+el.dataset.s >= 60) el.setAttribute('data-hi', ''); });

  // Thème sombre
  const tt = $('#theme-toggle');
  if (tt) tt.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
  });

  // Puces de compétences -> champ texte
  $$('.chips[data-target]').forEach(group => {
    const input = document.getElementById(group.dataset.target);
    const read = () => input.value.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
    const paint = () => { const cur = read(); $$('.chip', group).forEach(c => c.classList.toggle('on', cur.includes(c.textContent.toLowerCase()))); };
    group.addEventListener('click', e => {
      const chip = e.target.closest('.chip'); if (!chip) return;
      const name = chip.textContent.toLowerCase(); let cur = read();
      cur = cur.includes(name) ? cur.filter(s => s !== name) : cur.concat(name);
      input.value = cur.join(', '); paint();
    });
    input.addEventListener('input', paint); paint();
  });

  // Sauvegarder une offre
  document.addEventListener('click', async e => {
    const btn = e.target.closest('.save'); if (!btn) return;
    try {
      const r = await api('/api/save/' + btn.dataset.id, { method: 'POST' });
      btn.classList.toggle('on', r.saved); btn.setAttribute('aria-pressed', r.saved);
      toast(r.saved ? 'Offre sauvegardée' : 'Offre retirée des sauvegardes');
    } catch (err) { /* redirigé si non connecté */ }
  });

  // Curseur du score minimum
  const range = $('#min-range'), out = $('#min-out');
  if (range && out) range.addEventListener('input', () => out.textContent = range.value);

  // Actions admin
  const scrape = $('#btn-scrape'), demo = $('#btn-demo');
  if (scrape) scrape.addEventListener('click', async () => {
    scrape.disabled = true; toast('Scraping en cours… cela peut prendre une minute');
    try {
      const r = await api('/api/admin/scrape', { method: 'POST' });
      if (r.busy) toast('Un scraping est déjà en cours');
      else {
        const failed = Object.entries(r.report).filter(([, v]) => !v.ok).map(([k]) => k);
        toast(r.new + ' nouvelle(s) offre(s) sur ' + r.fetched + ' récupérées' + (failed.length ? ' · échec : ' + failed.join(', ') : ''));
        setTimeout(() => location.reload(), 1800);
      }
    } catch (err) { toast('Erreur pendant le scraping'); }
    scrape.disabled = false;
  });
  if (demo) demo.addEventListener('click', async () => {
    const r = await api('/api/admin/demo', { method: 'POST' });
    toast(r.added + ' offre(s) de démonstration ajoutée(s)');
    setTimeout(() => location.reload(), 1200);
  });
})();
