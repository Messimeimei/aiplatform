async function loadPortrait(){
  const sy = document.getElementById('sy').value;
  const ey = document.getElementById('ey').value;
  const url = `/api/portrait/${itemId}?start_year=${sy||''}&end_year=${ey||''}`;
  const res = await fetch(url);
  const data = await res.json();
  const chart = echarts.init(document.getElementById('graph'));
  chart.setOption({
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      data: (data.nodes||[]).map(n=>({
        id: String(n.id), name: n.name, category: n.kind, value: n.field, symbolSize: 40
      })),
      links: (data.links||[]).map(e=>({source:String(e.source), target:String(e.target), value:e.rel})),
      force: { repulsion: 260, edgeLength: 160 }
    }],
    legend: {}
  });
}
window.onload = loadPortrait;
