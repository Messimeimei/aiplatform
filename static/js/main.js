async function loadHot() {
    const res = await fetch('/api/hot');
    const data = await res.json();
    const el = document.getElementById('hot');
    if (!el) return;
    el.innerHTML = (data || []).map(d => `<a href="/results?q=${encodeURIComponent(d.kw)}">${d.kw}</a>`).join(' ');
}

async function loadResults(q, kind) {
    const field = document.getElementById('field').value || '';
    const country = document.getElementById('country').value || '';
    const sort = document.getElementById('sort').value || 'rel';
    const url = `/api/search?q=${encodeURIComponent(q)}&kind=${kind || ''}&field=${encodeURIComponent(field)}&country=${encodeURIComponent(country)}&sort=${sort}`;
    const res = await fetch(url);
    const items = await res.json();
    const ul = document.getElementById('list');
    ul.innerHTML = (items || []).map(it => `
    <li class="card">
      <div class="title"><a href="/detail/${it.id}">${it.name}</a></div>
      <div class="meta">${it.kind} | ${it.field} | ${it.country} | ${it.year}</div>
      <div class="abs">${(it.abstract || '').slice(0, 90)}...</div>
      <div class="score">关键性：${it.key_score}</div>
    </li>
  `).join('');
}
