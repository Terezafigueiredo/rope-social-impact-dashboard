/* Funções utilitárias compartilhadas */
window.ROPE = window.ROPE || {};
(function (R) {
  'use strict';

  R.NOMES = {AC:'Acre',AL:'Alagoas',AP:'Amapá',AM:'Amazonas',BA:'Bahia',CE:'Ceará',DF:'Distrito Federal',ES:'Espírito Santo',GO:'Goiás',MA:'Maranhão',MT:'Mato Grosso',MS:'Mato Grosso do Sul',MG:'Minas Gerais',PA:'Pará',PB:'Paraíba',PR:'Paraná',PE:'Pernambuco',PI:'Piauí',RJ:'Rio de Janeiro',RN:'Rio Grande do Norte',RS:'Rio Grande do Sul',RO:'Rondônia',RR:'Roraima',SC:'Santa Catarina',SP:'São Paulo',SE:'Sergipe',TO:'Tocantins'};

  R.fmt = n => Number(n).toLocaleString('pt-BR');
  R.pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
  R.esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  R.plural = (n, um, varios) => `${R.fmt(n)} ${n === 1 ? um : varios}`;
  R.espera = ms => new Promise(r => setTimeout(r, ms));

  /* Estados restritos podem vir só com "totalMax" (total exato não publicado) */
  R.mascarado = d => !!d && d.total == null && d.totalMax != null;
  R.numTotal = d => (R.mascarado(d) ? `<${d.totalMax + 1}` : R.fmt(d.total));
  R.textoTotal = (d, um, varios) => (R.mascarado(d) ? `menos de ${d.totalMax + 1} ${varios}` : R.plural(d.total, um, varios));

  /* Preferência de movimento: segue o sistema e pode ser trocada pelo botão */
  const consulta = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  let salvo = null;
  try { salvo = localStorage.getItem('rope-movimento'); } catch (e) { /* armazenamento indisponível */ }
  R.semMovimento = salvo ? salvo === 'off' : !!(consulta && consulta.matches);
  const ouvintes = [];
  R.aoMudarMovimento = fn => ouvintes.push(fn);
  R.definirMovimento = semMov => {
    R.semMovimento = semMov;
    document.documentElement.classList.toggle('sem-movimento', semMov);
    try { localStorage.setItem('rope-movimento', semMov ? 'off' : 'on'); } catch (e) { /* ignora */ }
    ouvintes.forEach(fn => fn(semMov));
  };
  document.documentElement.classList.toggle('sem-movimento', R.semMovimento);

  /* Tooltip único, que nunca sai da tela */
  const tip = () => document.getElementById('tooltip');
  R.mostrarTooltip = (evento, html) => {
    const t = tip(); t.innerHTML = html; t.hidden = false;
    const w = t.offsetWidth, h = t.offsetHeight;
    let x = evento.clientX + 14, y = evento.clientY + 14;
    if (x + w > innerWidth - 8) x = evento.clientX - w - 14;
    if (y + h > innerHeight - 8) y = evento.clientY - h - 14;
    t.style.left = Math.max(8, x) + 'px'; t.style.top = Math.max(8, y) + 'px';
  };
  R.esconderTooltip = () => { tip().hidden = true; };
  R.ligarTooltip = (el, html) => {
    el.addEventListener('mousemove', e => R.mostrarTooltip(e, typeof html === 'function' ? html() : html));
    el.addEventListener('mouseleave', R.esconderTooltip);
  };

  /* Contagem progressiva dos números */
  R.contar = (el, alvo, sufixo = '', ms = 1400) => {
    if (R.semMovimento) { el.textContent = R.fmt(alvo) + sufixo; return; }
    const t0 = performance.now();
    const passo = t => {
      const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
      el.textContent = R.fmt(Math.round(alvo * e)) + sufixo;
      if (k < 1) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
  };
})(window.ROPE);
