/* Componentes de visualização: colunas, barras, rosca e divisão.
   Todos trazem rótulos e números escritos (nada depende só da cor)
   e uma descrição em texto para leitores de tela. */
(function (R) {
  'use strict';
  const G = R.graficos = {};

  /* Colunas por ano. Recebe {2017: n, ...} e o intervalo a exibir (o mesmo eixo para Brasil e estados).
     Sem intervalo, usa o primeiro e o último ano presentes nos dados. */
  G.colunas = (alvo, anos, descricao, de, ate) => {
    const chaves = Object.keys(anos).map(Number).filter(Number.isFinite);
    de = de ?? Math.min(...chaves); ate = ate ?? Math.max(...chaves);
    const lista = [];
    for (let a = de; a <= ate; a++) lista.push([a, anos[a] || 0]);
    const max = Math.max(1, ...lista.map(x => x[1]));
    alvo.innerHTML = lista.map(([a, v]) => `
      <div class="coluna ${v ? '' : 'coluna--zero'}" data-ano="${a}" data-v="${v}">
        <span class="coluna__valor" aria-hidden="true">${v || ''}</span>
        <div class="coluna__barra" data-h="${(v / max) * 100}"></div>
        <span class="coluna__ano" aria-hidden="true"><span class="ano-longo">${a}</span><span class="ano-curto">’${String(a).slice(2)}</span></span>
      </div>`).join('') +
      `<table class="sr-only"><caption>${R.esc(descricao)}</caption><thead><tr><th scope="col">Ano</th><th scope="col">Sonhos</th></tr></thead><tbody>${lista.map(([a, v]) => `<tr><td>${a}</td><td>${v}</td></tr>`).join('')}</tbody></table>`;
    alvo.querySelectorAll('.coluna').forEach(c => R.ligarTooltip(c, `<b>${c.dataset.ano}</b><br>${R.plural(+c.dataset.v, 'sonho realizado', 'sonhos realizados')}`));
    G.animar(alvo);
  };

  /* Barras horizontais com valor e percentual. Recebe [[rótulo, n], ...] */
  G.barras = (lista, total, opcoes = {}) => {
    const max = Math.max(1, ...lista.map(x => x[1]));
    const desc = opcoes.descricao || '';
    return `<div class="barras ${opcoes.ouro ? 'barras--ouro' : ''}" role="list" aria-label="${R.esc(desc)}">${lista.map(([r, v]) => `
      <div class="barra" role="listitem" aria-label="${R.esc(r)}: ${v} (${R.pct(v, total)}%)">
        <span class="barra__rotulo" aria-hidden="true">${R.esc(r)}</span>
        <span class="barra__trilho" aria-hidden="true"><span class="barra__preench" data-w="${(v / max) * 100}"></span></span>
        <span class="barra__valor" aria-hidden="true"><b>${v}</b> · ${R.pct(v, total)}%</span>
      </div>`).join('')}</div>`;
  };

  /* Rosca (faixas etárias). Cores com rótulos e percentuais na legenda */
  const CORES = ['#FFDF8F', '#E8B04A', '#C9A2FF', '#8B5CD6'];
  G.rosca = (lista, centroNum, centroTxt, descricao) => {
    const total = lista.reduce((s, x) => s + x[1], 0) || 1, r = 52, C = 2 * Math.PI * r;
    let acumulado = 0;
    const fatias = lista.map(([, v], i) => {
      const comp = (v / total) * C, gap = v ? Math.min(3, comp / 3) : 0;
      const s = `<circle class="rosca__fatia" r="${r}" cx="66" cy="66" stroke="${CORES[i]}" stroke-dasharray="0 ${C}" data-d="${Math.max(0, comp - gap)} ${C}" stroke-dashoffset="${-acumulado}" transform="rotate(-90 66 66)"/>`;
      acumulado += comp; return s;
    }).join('');
    return `<div class="rosca">
      <svg viewBox="0 0 132 132" role="img" aria-label="${R.esc(descricao)}"><circle r="${r}" cx="66" cy="66" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="18"/>${fatias}
        <text class="rosca__centro" x="66" y="64"><tspan class="n" x="66">${R.esc(centroNum)}</tspan><tspan class="t" x="66" dy="18">${R.esc(centroTxt)}</tspan></text></svg>
      <ul class="legenda">${lista.map(([k, v], i) => `<li><i style="background:${CORES[i]}" aria-hidden="true"></i><span>${R.esc(k)} anos</span><b>${R.pct(v, total)}% <span style="color:var(--texto-fraco);font-weight:600">(${v})</span></b></li>`).join('')}</ul>
    </div>`;
  };

  /* Dispara as transições depois que os elementos estão na tela */
  G.animar = (raiz, atraso = 60) => {
    const aplicar = () => {
      raiz.querySelectorAll('[data-w]').forEach(e => { e.style.width = e.dataset.w + '%'; });
      raiz.querySelectorAll('[data-h]').forEach(e => { e.style.height = e.dataset.h + '%'; });
      raiz.querySelectorAll('[data-d]').forEach(e => { e.setAttribute('stroke-dasharray', e.dataset.d); });
      raiz.querySelectorAll('[data-flex]').forEach(e => { e.style.flex = e.dataset.flex; });
    };
    R.semMovimento ? aplicar() : setTimeout(() => requestAnimationFrame(aplicar), atraso);
  };
})(window.ROPE);
