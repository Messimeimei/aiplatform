async function loadRank() {
    const year = document.getElementById('year').value;
    const field = document.getElementById('field').value;
    const url = `/api/ranking?year=${year || ''}&field=${encodeURIComponent(field || '')}`;
    const data = await (await fetch(url)).json();
    const x = data.map(d => d.name);
    const y = data.map(d => d.key_score);
    const bar = echarts.init(document.getElementById('bar'));
    bar.setOption({
        tooltip: {}, xAxis: {type: 'category', data: x, axisLabel: {rotate: 30}}, yAxis: {type: 'value'},
        series: [{type: 'bar', data: y}]
    });
}

window.onload = loadRank;
