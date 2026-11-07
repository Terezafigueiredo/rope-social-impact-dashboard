/* Mapa interativo: carrega os contornos dos estados (com plano B offline em grade),
   desenha estados, contorno luminoso e marcadores, e faz o zoom animado. */
(function (R) {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.getElementById('mapa');
  const camada = document.getElementById('zoom');
  const W = 1000, H = 920;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

  // Plano B: mapa em grade (cartograma) com os 27 estados
  const GRADE = {RR:[2,0],AP:[4,0],AM:[1,1],PA:[3,1],MA:[4,1],CE:[5,1],RN:[6,1],AC:[0,2],RO:[1,2],MT:[2,2],TO:[3,2],PI:[4,2],PE:[5,2],PB:[6,2],GO:[3,3],BA:[4,3],SE:[5,3],AL:[6,3],MS:[2,4],DF:[3,4],MG:[4,4],ES:[5,4],SP:[3,5],RJ:[4,5],PR:[3,6],SC:[3,7],RS:[2,8]};
  // Lado do rótulo de cada marcador, para não colidir com vizinhos
  const LADO = {SP:'esq', RJ:'dir', MG:'dir', PE:'dir', AP:'dir'};

  const el = (tag, attrs = {}, pai = camada) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(e);
    return e;
  };

  const M = R.mapa = { formas: {}, modoGrade: false, zoom: {s: 1, tx: 0, ty: 0} };
  let contagens = {}, dadosUF = {}, maximo = 1, ao = {}, anim = 0, escalaPino = 1;

  /* ---------- geometria ---------- */
  const area = r => { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]); return a / 2; };
  const centroide = r => { let x = 0, y = 0, a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const f = r[j][0] * r[i][1] - r[i][0] * r[j][1]; x += (r[j][0] + r[i][0]) * f; y += (r[j][1] + r[i][1]) * f; a += f; } a /= 2; return a ? [x / (6 * a), y / (6 * a)] : r[0]; };

  function desenharGeo(geo) {
    const feats = [];
    for (const f of geo.features || []) {
      const p = f.properties || {};
      const uf = String(p.uf || '').toUpperCase();
      if (!R.NOMES[uf] || !f.geometry) continue;
      const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates : [];
      if (polys.length) feats.push({uf, polys});
    }
    if (feats.length < 20) throw new Error('mapa incompleto');
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    feats.forEach(f => f.polys.forEach(p => p.forEach(r => r.forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }))));
    const lonlat = x0 >= -80 && x1 <= -25 && y0 >= -40 && y1 <= 10;
    const kx = lonlat ? Math.cos(-15 * Math.PI / 180) : 1;
    // Orientação: Roraima precisa ficar acima do Rio Grande do Sul
    const cy = uf => { const f = feats.find(f => f.uf === uf); return f ? centroide(f.polys[0][0])[1] : 0; };
    const inverter = lonlat ? true : cy('RR') > cy('RS');
    const sx = (x1 - x0) * kx, sy = y1 - y0, s = Math.min((W - 40) / sx, (H - 40) / sy);
    const ox = (W - sx * s) / 2, oy = (H - sy * s) / 2;
    const P = ([x, y]) => [ox + (x - x0) * kx * s, inverter ? oy + (y1 - y) * s : oy + (y - y0) * s];

    const brilho = el('g', {class: 'contorno-brilho', filter: 'url(#brilho-mapa)', 'aria-hidden': 'true'});
    const estados = el('g', {class: 'estados'});
    for (const f of feats) {
      let d = '', maior = null, ma = 0;
      for (const poly of f.polys) {
        const aneis = poly.map(r => r.map(P));
        aneis.forEach(r => { d += 'M' + r.map(p => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('L') + 'Z'; });
        const a = Math.abs(area(aneis[0])); if (a > ma) { ma = a; maior = aneis[0]; }
      }
      el('path', {d}, brilho);
      const forma = el('path', {d, class: 'uf'}, estados);
      const c = centroide(maior);
      const bb = {x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9};
      maior.forEach(([x, y]) => { bb.x0 = Math.min(bb.x0, x); bb.x1 = Math.max(bb.x1, x); bb.y0 = Math.min(bb.y0, y); bb.y1 = Math.max(bb.y1, y); });
      M.formas[f.uf] = {el: forma, cx: c[0], cy: c[1], bb};
    }
    document.getElementById('credito-mapa').textContent = 'Contornos dos estados: Malha territorial do IBGE';
  }

  function desenharGrade() {
    M.modoGrade = true;
    const S = 96, g = 8, ox = (W - 7 * S) / 2, oy = (H - 9 * S) / 2;
    const estados = el('g', {class: 'estados'});
    for (const uf in GRADE) {
      const [c, r] = GRADE[uf], x = ox + c * S, y = oy + r * S;
      const grupo = el('g', {class: 'ladrilho'}, estados);
      const forma = el('rect', {x: x + g / 2, y: y + g / 2, width: S - g, height: S - g, rx: 14, class: 'uf'}, grupo);
      if (!contagens[uf]) el('text', {x: x + S / 2, y: y + S / 2}, grupo).textContent = uf;
      M.formas[uf] = {el: forma, cx: x + S / 2, cy: y + S / 2 + 6, bb: {x0: x, y0: y, x1: x + S, y1: y + S}};
    }
    document.getElementById('credito-mapa').textContent = 'Mapa em grade (modo offline)';
    document.getElementById('mapa-status').textContent = 'Mapa geográfico indisponível: exibindo mapa em grade.';
  }

  /* ---------- cores e marcadores ---------- */
  function corDe(n) {
    if (!n) return null;
    const t = Math.log(n) / Math.log(Math.max(2, maximo)); // escala log: o RJ concentra a maioria
    const a = [125, 85, 199], b = [201, 162, 255], k = 0.25 + 0.75 * t;
    return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * k)).join(',')})`;
  }
  const PINO = 'M0 0C-2-6-10-11-10-19a10 10 0 0 1 20 0c0 8-8 13-10 19z';

  function decorar() {
    const pinos = el('g', {class: 'pinos', 'aria-hidden': 'true'});
    for (const uf in M.formas) {
      const f = M.formas[uf], n = contagens[uf] || 0, nome = R.NOMES[uf], d = dadosUF[uf];
      const texto = n ? R.textoTotal(d, 'sonho realizado', 'sonhos realizados') : '';
      if (n) {
        f.el.style.fill = corDe(n);
        f.el.classList.add('uf--com');
        f.el.setAttribute('tabindex', '0');
        f.el.setAttribute('role', 'button');
        f.el.setAttribute('aria-label', `${nome}: ${texto}. Pressione Enter para ver detalhes.`);
        f.el.addEventListener('click', e => { e.stopPropagation(); ao.selecionar && ao.selecionar(uf); });
        f.el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ao.selecionar && ao.selecionar(uf); } });
        const g = el('g', {class: 'pino'}, pinos);
        el('circle', {class: 'pino__onda', cx: 0, cy: -2, r: 9}, g);
        el('path', {class: 'pino__corpo', d: PINO}, g);
        el('circle', {class: 'pino__furo', cx: 0, cy: -19, r: 4}, g);
        const esq = LADO[uf] === 'esq', ax = esq ? -14 : 14;
        const t1 = el('text', {class: 'pino__uf', x: ax, y: -16, 'text-anchor': esq ? 'end' : 'start', 'font-size': 19}, g); t1.textContent = uf;
        const t2 = el('text', {class: 'pino__num', x: ax, y: 3, 'text-anchor': esq ? 'end' : 'start', 'font-size': 14}, g); t2.textContent = R.numTotal(d);
        f.pino = g;
      } else {
        f.el.setAttribute('aria-hidden', 'true');
      }
      R.ligarTooltip(f.el, `<b>${nome}</b><br>${n ? R.esc(texto) : 'Ainda sem sonhos registrados'}`);
    }
    svg.addEventListener('click', () => ao.fundo && ao.fundo());
    medirPino(); aplicarZoom(M.zoom);
  }

  /* Marcadores mantêm tamanho legível em qualquer largura e zoom */
  function medirPino() {
    const largura = svg.clientWidth || 600;
    const unidadesPorPx = Math.max(W / largura, H / (svg.clientHeight || 600));
    escalaPino = Math.min(2.4, Math.max(0.8, unidadesPorPx * 0.95));
  }
  function aplicarZoom(z) {
    M.zoom = z;
    camada.setAttribute('transform', `translate(${z.tx.toFixed(2)},${z.ty.toFixed(2)}) scale(${z.s.toFixed(4)})`);
    for (const uf in M.formas) {
      const f = M.formas[uf];
      if (f.pino) f.pino.setAttribute('transform', `translate(${f.cx.toFixed(1)},${f.cy.toFixed(1)}) scale(${(escalaPino / z.s).toFixed(4)})`);
    }
  }
  function animarZoom(alvo, ms = 900) {
    return new Promise(fim => {
      cancelAnimationFrame(anim);
      if (R.semMovimento) { aplicarZoom(alvo); return fim(); }
      const de = {...M.zoom}, t0 = performance.now();
      const passo = t => {
        let k = Math.min(1, (t - t0) / ms);
        k = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; // easing cinematográfico
        aplicarZoom({s: de.s + (alvo.s - de.s) * k, tx: de.tx + (alvo.tx - de.tx) * k, ty: de.ty + (alvo.ty - de.ty) * k});
        k < 1 ? (anim = requestAnimationFrame(passo)) : fim();
      };
      anim = requestAnimationFrame(passo);
    });
  }

  /* ---------- API usada pelo app ---------- */
  M.focar = uf => {
    const f = M.formas[uf];
    svg.classList.add('mapa--foco');
    for (const k in M.formas) M.formas[k].el.classList.toggle('uf--sel', k === uf);
    const bw = f.bb.x1 - f.bb.x0, bh = f.bb.y1 - f.bb.y0;
    const s = Math.max(1, Math.min(M.modoGrade ? 1.8 : 5, 0.5 * Math.min(W / bw, H / bh)));
    return animarZoom({s, tx: W / 2 - f.cx * s, ty: H / 2 - f.cy * s});
  };
  M.resetar = () => {
    svg.classList.remove('mapa--foco');
    for (const k in M.formas) M.formas[k].el.classList.remove('uf--sel');
    return animarZoom({s: 1, tx: 0, ty: 0}, 750);
  };
  /* Posição na tela do centro de um estado (ou do Brasil), para os cartões saírem dele */
  M.centroTela = uf => {
    const pt = svg.createSVGPoint();
    if (uf && M.formas[uf]) { pt.x = M.formas[uf].cx; pt.y = M.formas[uf].cy; return pt.matrixTransform(camada.getScreenCTM()); }
    pt.x = W / 2; pt.y = H / 2; return pt.matrixTransform(svg.getScreenCTM());
  };

  /* Contornos vêm de js/mapa-ufs.js (malha do IBGE hospedada no próprio site):
     nenhum script de terceiros é executado. Sem o arquivo, usa o mapa em grade. */
  M.carregar = async (dados, eventos) => {
    ao = eventos;
    // Total mascarado: o estado recebe a cor mais clara da escala, igual para todos os restritos
    dadosUF = dados;
    for (const uf in R.NOMES) contagens[uf] = dados[uf] ? (R.mascarado(dados[uf]) ? 1 : dados[uf].total) : 0;
    maximo = Math.max(...Object.values(contagens));
    try {
      if (window.MAPA_UFS) desenharGeo(window.MAPA_UFS);
    } catch (e) { camada.innerHTML = ''; M.formas = {}; }
    if (!Object.keys(M.formas).length) desenharGrade();
    decorar();
    let espera;
    addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(() => { medirPino(); aplicarZoom(M.zoom); }, 120); });
  };
})(window.ROPE);
