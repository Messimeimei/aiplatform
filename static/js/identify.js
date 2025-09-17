async function idText(){
  const text = document.getElementById('txt').value||'';
  const res = await fetch('/api/identify/text',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text})});
  const data = await res.json();
  document.getElementById('tags').innerHTML = (data.terms||[]).map(t=>`<span class="tag ${t.type=='关键技术'?'tech':'prod'}">${t.term}</span>`).join(' ');
}
async function idFile(){
  const f = document.getElementById('file').files[0];
  if(!f) return;
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/api/identify/file',{method:'POST', body:fd});
  const data = await res.json();
  document.getElementById('fileTags').innerHTML = (data.terms||[]).map(t=>`<span class="tag ${t.type=='关键技术'?'tech':'prod'}">${t.term}</span>`).join(' ');
}
