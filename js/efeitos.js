/* Céu animado: estrelas cintilando e partículas douradas (leve, ~30 fps, pausa quando oculto) */
(function (R) {
  'use strict';
  const canvas = document.getElementById('estrelas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let estrelas = [], particulas = [], largura = 0, altura = 0, dpr = 1, quadro = 0, ultimo = 0;

  let semente = 11;
  const aleatorio = () => (semente = (semente * 16807) % 2147483647) / 2147483647;

  function montar() {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    largura = innerWidth; altura = innerHeight;
    canvas.width = largura * dpr; canvas.height = altura * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    semente = 11;
    const qtd = Math.round(Math.min(220, (largura * altura) / 7000));
    estrelas = Array.from({length: qtd}, () => ({
      x: aleatorio() * largura, y: aleatorio() * altura, r: aleatorio() * 1.3 + 0.25,
      base: 0.25 + aleatorio() * 0.55, vel: 0.6 + aleatorio() * 1.6, fase: aleatorio() * 6.28,
      cruz: aleatorio() > 0.94
    }));
    particulas = Array.from({length: Math.round(qtd / 7)}, () => novaParticula(true));
    desenhar(performance.now());
  }
  function novaParticula(inicio) {
    return { x: aleatorio() * largura, y: inicio ? aleatorio() * altura : altura + 10, r: 0.8 + aleatorio() * 1.6,
      vy: 0.12 + aleatorio() * 0.28, vx: (aleatorio() - 0.5) * 0.15, fase: aleatorio() * 6.28 };
  }
  function desenhar(t) {
    ctx.clearRect(0, 0, largura, altura);
    const s = t / 1000;
    for (const e of estrelas) {
      const a = R.semMovimento ? e.base : e.base * (0.55 + 0.45 * Math.sin(s * e.vel + e.fase));
      ctx.fillStyle = `rgba(255,244,220,${a})`;
      ctx.beginPath(); ctx.arc(e.x, e.y, e.r, 0, 6.283); ctx.fill();
      if (e.cruz) {
        ctx.strokeStyle = `rgba(255,223,143,${a * 0.8})`; ctx.lineWidth = 0.8;
        const c = e.r * 5;
        ctx.beginPath(); ctx.moveTo(e.x - c, e.y); ctx.lineTo(e.x + c, e.y); ctx.moveTo(e.x, e.y - c); ctx.lineTo(e.x, e.y + c); ctx.stroke();
      }
    }
    for (const p of particulas) {
      const a = 0.35 + 0.35 * Math.sin(s * 1.3 + p.fase);
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4);
      g.addColorStop(0, `rgba(255,223,143,${a})`); g.addColorStop(1, 'rgba(255,223,143,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 4, 0, 6.283); ctx.fill();
    }
  }
  function ciclo(t) {
    quadro = requestAnimationFrame(ciclo);
    if (t - ultimo < 33) return; // ~30 fps é suficiente
    ultimo = t;
    for (const p of particulas) {
      p.y -= p.vy; p.x += p.vx + Math.sin(t / 2000 + p.fase) * 0.08;
      if (p.y < -10) Object.assign(p, novaParticula(false));
    }
    desenhar(t);
  }
  function iniciar() { if (!quadro && !R.semMovimento && !document.hidden) quadro = requestAnimationFrame(ciclo); }
  function parar() { cancelAnimationFrame(quadro); quadro = 0; desenhar(performance.now()); }

  let espera;
  addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(montar, 150); });
  document.addEventListener('visibilitychange', () => (document.hidden ? parar() : iniciar()));
  R.aoMudarMovimento(semMov => (semMov ? parar() : iniciar()));
  montar(); iniciar();
})(window.ROPE);
