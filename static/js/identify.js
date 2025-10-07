// ===== 文本识别 =====
async function idText() {
  const btn = document.getElementById('btnTextRun');
  const text = document.getElementById('txt').value.trim();
  if (!text) return alert('请输入文本内容');

  try {
    btn.disabled = true;
    btn.innerText = '识别中...';

    // ✅ 统一接口 /api/identify
    const res = await fetch('/api/identify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'text', text })
    });

    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // ✅ 渲染识别结果
    document.getElementById('tags').innerHTML = (data.tech || [])
      .map(t => `<span class="tag tech">${t}</span>`).join(' ')
      + (data.product?.length ? ' ' + data.product.map(p => `<span class="tag prod">${p}</span>`).join(' ') : '');

  } catch (err) {
    alert('识别失败：' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '开始识别';
  }
}


// ===== 文件识别 =====
async function idFile() {
  const btn = document.getElementById('btnFileRun');
  const f = document.getElementById('file').files[0];
  if (!f) return alert('请选择文件');

  try {
    btn.disabled = true;
    btn.innerText = '识别中...';

    const fd = new FormData();
    fd.append('mode', 'file');
    fd.append('file', f);

    // ✅ 统一接口 /api/identify
    const res = await fetch('/api/identify', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    document.getElementById('fileTags').innerHTML = (data.tech || [])
      .map(t => `<span class="tag tech">${t}</span>`).join(' ')
      + (data.product?.length ? ' ' + data.product.map(p => `<span class="tag prod">${p}</span>`).join(' ') : '');

  } catch (err) {
    alert('识别失败：' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = '开始识别';
  }
}
