/* Painel de detalhamento: monta os cartões do Brasil ou de um estado */
(function (R) {
  'use strict';
  const G = R.graficos;
  const ICONES = {
    coracao: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    pessoas: '<circle cx="12" cy="8" r="3"/><circle cx="5.5" cy="10" r="2.2"/><circle cx="18.5" cy="10" r="2.2"/><path d="M6.5 19a5.5 5.5 0 0 1 11 0M1.8 18a3.8 3.8 0 0 1 4.6-3.6M22.2 18a3.8 3.8 0 0 0-4.6-3.6"/>',
    presente: '<rect x="3.5" y="9" width="17" height="11" rx="1.5"/><path d="M2.5 9h19v-3h-19zM12 6v14M12 6c-1.5-3-5-3.5-5.5-1.5S9 6 12 6zM12 6c1.5-3 5-3.5 5.5-1.5S15 6 12 6z"/>',
    maos: '<path d="M3 13l4-3 3 1 3-2 3 2-4 3c-1 .7-2 .7-3 0M21 13l-4-3M7 10l-4 6 3 2M17 10l4 6-3 2M10 16l2 2 2-1 2 1"/>',
    predio: '<path d="M4 20V6l8-3 8 3v14M2 20h20M8 9h2M14 9h2M8 13h2M14 13h2M10.5 20v-3h3v3"/>',
    saude: '<path d="M12 21s-7.5-4.6-7.5-10.4A4.1 4.1 0 0 1 12 8a4.1 4.1 0 0 1 7.5 2.6C19.5 16.4 12 21 12 21z"/><path d="M12 11v5M9.5 13.5h5"/>',
    cadeado: '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5M12 14.5v2.5"/>',
    calendario: '<rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>'
  };
  const icone = (n, cls = '') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONES[n]}</svg>`;
  const titulo = (ic, txt) => `<h3 class="cartao__titulo">${icone(ic)}<span>${txt}</span></h3>`;
  const periodo = d => (d.first === d.last ? `em ${d.first}` : `de ${d.first} a ${d.last}`);

  function cartoesDe(chave, d, br) {
    const ehBrasil = chave === 'BR';
    const nomeCurto = ehBrasil ? 'no Brasil' : `em ${R.NOMES[chave]}`;
    const meta = R.DADOS_META, k = meta.limiteCelula;
    const omitido = motivo => `<p class="nota">${motivo}</p>`;
    const c = [];
    const mascarado = R.mascarado(d);
    const parteDoTotal = mascarado ? `menos de ${Math.ceil((100 * d.totalMax) / br.total)}%`
      : d.total / br.total < 0.01 ? 'menos de 1%' : `${R.pct(d.total, br.total)}%`;
    const numero = mascarado
      ? `<i aria-hidden="true" style="font-style:normal">${R.esc(R.numTotal(d))}</i><span class="sr-only">menos de ${d.totalMax + 1}</span>`
      : R.fmt(d.total);
    c.push(`<section class="cartao"><div class="mini">${icone('coracao')}<div>
      <strong>${numero}</strong><span>Sonhos realizados</span>
      <small>${ehBrasil ? `${periodo(d)}, em ${Object.keys(R.DADOS).length - 1} estados${d.semUF ? ` (e ${R.plural(d.semUF, 'sonho', 'sonhos')} sem estado identificado)` : ''}` : `${parteDoTotal} do total do Instituto${d.restrito ? '' : ` · ${periodo(d)}`}`}</small></div></div></section>`);
    c.push(`<section class="cartao"><div class="mini">${icone('pessoas')}<div>
      <strong>${d.impactN ? R.fmt(d.impact) : '—'}</strong><span>Pessoas impactadas</span>
      <small>${d.restrito ? 'Não exibido para proteger a privacidade' : d.impactN ? `Registrado em ${d.impactN} de ${R.plural(d.total, 'sonho', 'sonhos')}` : 'Sem registro suficiente para este estado'}</small></div></div></section>`);

    if (d.restrito) {
      c.push(`<section class="cartao cartao--largo"><div class="aviso">${icone('cadeado')}<p style="margin:0"><b style="color:var(--branco)">Detalhes omitidos para proteger a privacidade.</b><br>
        Com menos de ${meta.limiteDetalhe} sonhos registrados ${nomeCurto}, mostrar ano, idade, tipo de sonho, condição de saúde ou instituição poderia identificar uma pessoa. Por isso exibimos ${mascarado ? 'apenas que são menos de ' + meta.limiteDetalhe : 'apenas o total'}.</p></div></section>`);
      return c;
    }

    if (ehBrasil && d.detalheN < d.total) {
      c.push(`<section class="cartao cartao--largo"><div class="aviso">${icone('cadeado')}<p style="margin:0">Os detalhes abaixo somam os <b style="color:var(--branco)">${R.fmt(d.detalheN)} sonhos</b> dos estados com ${meta.limiteDetalhe} ou mais registros. Em cada estado, grupos com menos de ${k} pessoas aparecem somados em “outros”.</p></div></section>`);
    }

    // Tipos de sonho: o grupo "Outros tipos" (soma de categorias pequenas) fica sempre por último
    const OUTROS_TIPOS = 'Outros tipos';
    const totCat = d.cats.reduce((s, x) => s + x[1], 0);
    const visiveis = d.cats.slice(0, 6);
    const resto = d.cats.slice(6);
    c.push(`<section class="cartao cartao--largo">${titulo('presente', `Tipos de sonho <small>· ${ehBrasil ? 'Brasil' : chave}</small>`)}
      ${G.barras(visiveis, totCat, {descricao: `Tipos de sonho ${nomeCurto}`})}
      ${resto.length ? `<p class="nota">Também: ${resto.map(([n, v]) => `${R.esc(n)} (<b>${v}</b>)`).join(', ')}.</p>` : ''}
      ${d.cats.some(([n]) => n === OUTROS_TIPOS) ? `<p class="nota">“${OUTROS_TIPOS}” reúne categorias com menos de ${k} registros.</p>` : ''}</section>`);

    if (d.bands) {
      const faixas = Object.entries(d.bands);
      const comIdade = faixas.reduce((s, x) => s + x[1], 0);
      const resumoIdade = faixas.map(([f, v]) => `${f} anos: ${R.pct(v, comIdade)}%`).join('; ');
      const idade = d.ageAvg == null ? '' : `<div><strong>${d.ageAvg}</strong><span>idade média</span></div>`;
      c.push(`<section class="cartao cartao--largo">${titulo('pessoas', 'Faixa etária')}
        ${comIdade ? G.rosca(faixas, R.fmt(comIdade), 'com idade', `Faixa etária dos sonhadores ${nomeCurto}. ${resumoIdade}.`) : omitido('Sem idade registrada.')}
        <div class="par" style="margin-top:12px">${idade}<div><strong>${R.fmt(d.kids)}</strong><span>crianças e adolescentes</span></div></div></section>`);
    } else {
      c.push(`<section class="cartao cartao--largo">${titulo('pessoas', 'Faixa etária')}${omitido(`Não exibida: alguma faixa teria menos de ${k} pessoas.`)}</section>`);
    }

    const INDIVIDUAL = 'Indicação individual', OUTRAS = 'Outras origens';
    const valor = rotulo => (d.partners.find(([n]) => n === rotulo) || [, 0])[1];
    const instituicoes = d.partners.filter(([n]) => n !== INDIVIDUAL && n !== OUTRAS);
    const totParc = d.partners.reduce((s, x) => s + x[1], 0);
    const individuais = valor(INDIVIDUAL), outras = valor(OUTRAS);
    c.push(`<section class="cartao cartao--largo">${titulo('maos', `Instituições parceiras <small>· ${ehBrasil ? 'Brasil' : chave}</small>`)}
      <div class="par" style="margin-bottom:12px"><div><strong>${R.fmt(d.partnersN)}</strong><span>instituições indicaram sonhos</span></div></div>
      ${instituicoes.length ? G.barras(instituicoes.slice(0, 5), totParc, {descricao: `Instituições que mais indicaram sonhos ${nomeCurto}`, ouro: true}) : ''}
      ${individuais ? `<p class="nota">Outros <b>${individuais}</b> sonhos vieram de indicações individuais.</p>` : ''}
      ${outras ? `<p class="nota"><b>${outras}</b> ${outras === 1 ? 'sonho veio' : 'sonhos vieram'} de outras origens, que não são citadas pelo nome.</p>` : ''}</section>`);

    if (d.sex) {
      const mulheres = d.sex.Mulheres || 0, homens = d.sex.Homens || 0, totSexo = mulheres + homens;
      c.push(`<section class="cartao">${titulo('coracao', 'Quem sonhou')}
        <div class="divisao" role="img" aria-label="Mulheres: ${mulheres} (${R.pct(mulheres, totSexo)}%). Homens: ${homens} (${R.pct(homens, totSexo)}%).">
          <div data-flex="${mulheres}" style="flex:0;background:#C9A2FF"></div><div data-flex="${homens}" style="flex:0;background:#F0C35A"></div></div>
        <ul class="legenda" style="grid-template-columns:1fr">
          <li><i style="background:#C9A2FF" aria-hidden="true"></i><span>Mulheres</span><b>${R.pct(mulheres, totSexo)}% <span style="color:var(--texto-fraco);font-weight:600">(${mulheres})</span></b></li>
          <li><i style="background:#F0C35A" aria-hidden="true"></i><span>Homens</span><b>${R.pct(homens, totSexo)}% <span style="color:var(--texto-fraco);font-weight:600">(${homens})</span></b></li></ul></section>`);
    } else {
      c.push(`<section class="cartao">${titulo('coracao', 'Quem sonhou')}${omitido(`Não exibido: um dos grupos teria menos de ${k} pessoas.`)}</section>`);
    }

    const totIll = d.ills.reduce((s, x) => s + x[1], 0);
    c.push(`<section class="cartao">${titulo('saude', 'Condições de saúde')}
      ${totIll ? G.barras(d.ills.slice(0, 5), totIll, {descricao: `Grupos de condições de saúde ${nomeCurto}, agregados`}) : omitido('Sem registro suficiente.')}
      <p class="nota">Agrupamento geral, sem dados individuais. Grupos com menos de ${k} pessoas entram em “Outras”.</p></section>`);
    return c;
  }

  const P = R.painel = {};
  const alvo = () => document.getElementById('cartoes');

  /* Renderiza e anima os cartões saindo de um ponto da tela (o estado clicado) */
  P.mostrar = (chave, origem) => {
    const d = R.DADOS[chave], br = R.DADOS.BR, raiz = alvo();
    raiz.innerHTML = cartoesDe(chave, d, br).join('');
    const nome = document.getElementById('painel-nome');
    if (chave === 'BR') nome.textContent = 'Brasil';
    else {
      const partes = R.NOMES[chave].split(' ');
      const ultimo = partes.pop();
      nome.innerHTML = `${partes.length ? R.esc(partes.join(' ')) + ' ' : ''}<span class="destaque">${R.esc(ultimo)} (${chave})</span>`;
    }
    if (!R.semMovimento && origem && raiz.animate) {
      [...raiz.children].forEach((cartao, i) => {
        const r = cartao.getBoundingClientRect();
        const dx = origem.x - (r.left + r.width / 2), dy = origem.y - (r.top + r.height / 2);
        cartao.animate([
          {transform: `translate(${dx}px,${dy}px) scale(.06)`, opacity: 0},
          {offset: 0.55, opacity: 1},
          {transform: 'none', opacity: 1}
        ], {duration: 850, delay: i * 85, easing: 'cubic-bezier(.2,.9,.25,1.04)', fill: 'backwards'});
      });
    }
    G.animar(raiz, R.semMovimento ? 0 : 420);
  };

  /* Cartões voltam para dentro do estado antes de trocar o conteúdo */
  P.recolher = destino => {
    const raiz = alvo();
    if (R.semMovimento || !destino || !raiz.animate) return Promise.resolve();
    const filhos = [...raiz.children];
    return Promise.all(filhos.map((cartao, i) => {
      const r = cartao.getBoundingClientRect();
      const dx = destino.x - (r.left + r.width / 2), dy = destino.y - (r.top + r.height / 2);
      return cartao.animate([{transform: 'none', opacity: 1}, {transform: `translate(${dx}px,${dy}px) scale(.06)`, opacity: 0}],
        {duration: 420, delay: (filhos.length - 1 - i) * 35, easing: 'cubic-bezier(.5,0,.75,0)', fill: 'forwards'}).finished;
    }));
  };
})(window.ROPE);
