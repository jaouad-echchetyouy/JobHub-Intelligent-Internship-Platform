(function () {
  const list = document.getElementById('reco-list');
  const detail = document.getElementById('reco-detail');
  const fq = document.getElementById('f-q'), ft = document.getElementById('f-type'), fm = document.getElementById('f-mode');
  let items = [], current = null, timer = null;

  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const bar = (label, v) => `<div><div class="bar-top"><span>${label}</span><span>${v}%</span></div><div class="bar"><i style="width:${v}%"></i></div></div>`;
  const tags = (arr, cls) => arr.length ? arr.map(s => `<span class="tag ${cls}">${esc(s)}</span>`).join('') : '<span class="muted">Aucune</span>';

  function renderList() {
    if (!items.length) { list.innerHTML = '<div class="card empty"><h3>Aucune offre trouvée</h3><p class="muted">Modifie les filtres ou lance le scraping depuis le tableau de bord.</p></div>'; detail.innerHTML = ''; return; }
    list.innerHTML = items.map(o => `
      <button type="button" class="reco-item ${current && current.id === o.id ? 'on' : ''}" data-id="${o.id}" role="option">
        <div class="grow"><b>${esc(o.title)}</b><small>${esc(o.company)}${o.location ? ' · ' + esc(o.location) : ''}</small></div>
        <span class="score" ${o.score >= 60 ? 'data-hi' : ''}>${o.score}%</span>
      </button>`).join('');
  }

  function renderDetail(o) {
    if (!o) { detail.innerHTML = '<p class="muted">Sélectionne une offre.</p>'; return; }
    detail.innerHTML = `
      <div class="detail-head">
        <div><h2>${esc(o.title)}</h2><p class="muted">${esc(o.company)}</p>
          <div class="tags" style="margin-top:10px"><span class="badge">${esc(o.type)}</span><span class="badge m-${esc(o.mode.toLowerCase())}">${esc(o.mode)}</span>${o.location ? `<span class="tag">${esc(o.location)}</span>` : ''}</div></div>
        <div class="big-score"><b>${o.score}%</b><small class="muted">correspondance</small></div>
      </div>
      <div class="bars">${bar('Compétences', o.skills_pct)}${bar('Profil', o.text_pct)}${bar('Préférences', o.pref_pct)}</div>
      <div class="detail-sec"><h4>Description</h4><p class="muted">${esc(o.description) || 'Pas de description.'}</p></div>
      <div class="detail-sec"><h4>Pourquoi cette recommandation</h4><div class="why">${esc(o.why)}</div></div>
      <div class="detail-sec"><h4>Tu as déjà</h4><div class="tags">${tags(o.matching, 'good')}</div></div>
      <div class="detail-sec"><h4>À développer</h4><div class="tags">${tags(o.missing, 'bad')}</div></div>
      <div class="detail-actions">
        <button type="button" class="btn save ${o.saved ? 'on' : ''}" data-id="${o.id}" aria-pressed="${o.saved}">Sauvegarder</button>
        <a class="btn primary" href="${esc(o.url)}" target="_blank" rel="noopener">Postuler</a>
      </div>
      <p class="muted" style="margin-top:12px"><small>Source : ${esc(o.source)} · publiée le ${esc(o.posted)}</small></p>`;
  }

  async function load() {
    const p = new URLSearchParams({ q: fq.value.trim(), type: ft.value, mode: fm.value });
    const data = await api('/api/recommendations?' + p);
    items = data.items;
    document.getElementById('no-profile').hidden = data.has_profile;
    document.getElementById('reco-sub').textContent = data.total + ' offres analysées, triées par correspondance avec ton profil.';
    current = items.find(i => current && i.id === current.id) || items[0] || null;
    renderList(); renderDetail(current);
  }

  list.addEventListener('click', e => {
    const b = e.target.closest('.reco-item'); if (!b) return;
    current = items.find(i => i.id === +b.dataset.id);
    renderList(); renderDetail(current);
    if (window.innerWidth <= 1100) detail.scrollIntoView({ behavior: 'smooth' });
  });
  // Garder l'état "sauvegardé" synchronisé après un clic (géré par app.js)
  detail.addEventListener('click', e => {
    const b = e.target.closest('.save'); if (!b || !current) return;
    setTimeout(() => { current.saved = b.classList.contains('on'); }, 300);
  });
  [ft, fm].forEach(el => el.addEventListener('change', load));
  fq.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(load, 300); });
  load();
})();
