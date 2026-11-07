/* Orquestra a página: indicadores, seletor, gráfico por ano e navegação entre Brasil e estados */
(function (R) {
  'use strict';
  R.DADOS = window.DADOS;
  R.DADOS_META = Object.assign({limiteDetalhe: 10, limiteCelula: 5}, window.DADOS_META);
  const BR = R.DADOS.BR;
  // Detalhados por total; restritos depois, em ordem alfabética (a ordem não pode revelar quem tem mais)
  const ordem = uf => (R.DADOS[uf].restrito ? -1 : R.DADOS[uf].total);
  const estados = Object.keys(R.DADOS).filter(k => k !== 'BR')
    .sort((a, b) => ordem(b) - ordem(a) || (R.DADOS[a].restrito ? a.localeCompare(b) : 0));
  let atual = 'BR', ocupado = false;

  /* ---------- indicadores ---------- */
  const kpi = nome => document.querySelector(`[data-kpi="${nome}"]`);
  R.contar(kpi('sonhos'), BR.total);
  R.contar(kpi('estados'), estados.length);
  R.contar(kpi('pessoas'), BR.impact, '+');
  kpi('periodo').textContent = `${BR.first} – ${BR.last}`;
  kpi('periodo').setAttribute('aria-label', `de ${BR.first} a ${BR.last}`);
  document.getElementById('nota-pessoas').textContent =
    `* Pessoas impactadas: familiares, equipes de saúde e voluntários envolvidos, somados nos ${BR.impactN} de ${BR.total} sonhos em que esse número foi registrado.`;
  document.getElementById('nota-limite').textContent = R.DADOS_META.limiteDetalhe;
  document.getElementById('nota-celula').textContent = R.DADOS_META.limiteCelula;
  if (estados.some(uf => R.mascarado(R.DADOS[uf])))
    document.getElementById('nota-restritos').textContent = `apenas a indicação “menos de ${R.DADOS_META.limiteDetalhe}”, sem o número exato`;

  /* ---------- seletor (alternativa acessível ao mapa) ---------- */
  const lista = document.getElementById('seletor-lista');
  lista.innerHTML = estados.map(uf => `<li><button type="button" class="chip" data-uf="${uf}" aria-pressed="false" aria-label="${R.NOMES[uf]}: ${R.textoTotal(R.DADOS[uf], 'sonho', 'sonhos')}">${uf} <b>${R.esc(R.numTotal(R.DADOS[uf]))}</b></button></li>`).join('');
  lista.addEventListener('click', e => {
    const b = e.target.closest('.chip'); if (!b) return;
    b.getAttribute('aria-pressed') === 'true' ? voltar() : abrir(b.dataset.uf);
  });

  /* ---------- gráfico por ano ---------- */
  function atualizarAnos(chave) {
    const d = R.DADOS[chave], alvo = document.getElementById('grafico-anos');
    const escopo = document.getElementById('anos-escopo'), nota = document.getElementById('anos-nota');
    const usarBrasil = chave === 'BR' || d.restrito;
    const fonte = usarBrasil ? BR : d;
    escopo.textContent = `· ${usarBrasil ? 'Brasil' : R.NOMES[chave]}`;
    // Eixo do Brasil inteiro (primeiro ao último ano registrado): reconhece 2027 em diante sem mudar código
    R.graficos.colunas(alvo, fonte.years, `Sonhos realizados por ano, ${usarBrasil ? 'Brasil' : R.NOMES[chave]}`, BR.first, BR.last);
    const melhor = Object.entries(fonte.years).reduce((a, b) => (b[1] > a[1] ? b : a));
    // O ano em que os dados foram gerados ainda não terminou
    const anoGerado = Number(String(R.DADOS_META.gerado || '').slice(0, 4));
    const emAndamento = fonte.last === anoGerado && fonte.years[anoGerado] ? ` ${anoGerado} ainda está em andamento.` : '';
    const fora = usarBrasil && BR.anosIncluemRestritos === false && BR.detalheN < BR.total
      ? ` O gráfico do Brasil não inclui os ${R.fmt(BR.total - BR.detalheN)} sonhos de estados com menos de ${R.DADOS_META.limiteDetalhe} registros.` : '';
    nota.innerHTML = (d.restrito
      ? `Para proteger a privacidade, a distribuição por ano de ${R.esc(R.NOMES[chave])} não é exibida; o gráfico mostra o Brasil.`
      : `Ano com mais sonhos: <b>${melhor[0]}</b> (${melhor[1]}).${emAndamento}`) + fora;
  }

  /* ---------- navegação ---------- */
  const botaoVoltar = document.getElementById('botao-voltar');
  const tituloPainel = document.getElementById('painel-titulo');
  const estreito = () => matchMedia('(max-width: 900px)').matches;

  function marcarChips(uf) {
    lista.querySelectorAll('.chip').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.uf === uf)));
  }

  async function abrir(uf) {
    if (ocupado || uf === atual || !R.DADOS[uf]) return;
    ocupado = true; R.esconderTooltip();
    await R.painel.recolher(R.mapa.centroTela(atual === 'BR' ? null : atual));
    document.getElementById('dica').classList.add('oculta');
    await R.mapa.focar(uf);
    atual = uf; marcarChips(uf); botaoVoltar.hidden = false;
    R.painel.mostrar(uf, R.mapa.centroTela(uf));
    atualizarAnos(uf);
    tituloPainel.focus({preventScroll: true});
    if (estreito()) setTimeout(() => document.getElementById('painel').scrollIntoView({behavior: R.semMovimento ? 'auto' : 'smooth', block: 'start'}), R.semMovimento ? 0 : 500);
    ocupado = false;
  }

  async function voltar() {
    if (ocupado || atual === 'BR') return;
    ocupado = true; R.esconderTooltip();
    const anterior = atual;
    await R.painel.recolher(R.mapa.centroTela(anterior));
    await R.mapa.resetar();
    atual = 'BR'; marcarChips(null); botaoVoltar.hidden = true;
    document.getElementById('dica').classList.remove('oculta');
    R.painel.mostrar('BR', R.mapa.centroTela(null));
    atualizarAnos('BR');
    const forma = R.mapa.formas[anterior];
    if (forma && document.activeElement === botaoVoltar) forma.el.focus({preventScroll: true});
    ocupado = false;
  }

  botaoVoltar.addEventListener('click', voltar);
  // Esc sempre fecha o tooltip (WCAG 1.4.13) e, se houver estado aberto, volta ao Brasil
  addEventListener('keydown', e => { if (e.key === 'Escape') { R.esconderTooltip(); voltar(); } });

  /* ---------- botão de animações ---------- */
  const botaoMov = document.getElementById('botao-movimento');
  const rotularMov = () => {
    botaoMov.setAttribute('aria-pressed', String(R.semMovimento));
    botaoMov.querySelector('span').textContent = R.semMovimento ? 'Ativar animações' : 'Pausar animações';
    botaoMov.querySelector('path').setAttribute('d', R.semMovimento ? 'M8 5l11 7-11 7z' : 'M8 5v14M16 5v14');
  };
  botaoMov.addEventListener('click', () => { R.definirMovimento(!R.semMovimento); rotularMov(); });
  rotularMov();

  /* ---------- início ---------- */
  atualizarAnos('BR');
  R.mapa.carregar(R.DADOS, {selecionar: abrir, fundo: voltar}).then(() => {
    R.painel.mostrar('BR', R.mapa.centroTela(null));
  });
})(window.ROPE);
