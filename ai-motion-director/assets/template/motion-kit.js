/* motion-kit.js — primitivas de motion graphics para Canvas 2D, 100% determinísticas.
 * Toda função é pura em relação ao tempo `t` (segundos): nada de Date.now(), Math.random()
 * ou estado acumulado. É isso que permite renderizar frame a frame e dar scrub para qualquer t.
 * Uso: <script src="motion-kit.js"></script>  → objeto global `M`.
 */
const M = (() => {
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, k) => a + (b - a) * k;
  const map = (v, a, b, c, d) => lerp(c, d, clamp((v - a) / (b - a)));
  const prog = (t, a, b) => clamp((t - a) / (b - a));           // progresso 0..1 de a até b

  /* ---- easings: escolha pela física que a narrativa pede, não por gosto ---- */
  const E = {
    linear: k => k,
    inCubic: k => k * k * k,
    outCubic: k => 1 - Math.pow(1 - k, 3),
    inOutCubic: k => (k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    outExpo: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),       // chegada decidida, "snap"
    inExpo: k => (k <= 0 ? 0 : Math.pow(2, 10 * k - 10)),        // aceleração de tensão
    inOutExpo: k => (k <= 0 ? 0 : k >= 1 ? 1 : k < .5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2),
    outBack: (k, s = 1.70158) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2),
    inBack: (k, s = 1.70158) => (s + 1) * k * k * k - s * k * k,   // antecipação
    outElastic: k => (k <= 0 ? 0 : k >= 1 ? 1 : Math.pow(2, -10 * k) * Math.sin((k * 10 - .75) * (2 * Math.PI) / 3) + 1),
    outBounce: k => { const n = 7.5625, d = 2.75; if (k < 1 / d) return n * k * k; if (k < 2 / d) return n * (k -= 1.5 / d) * k + .75; if (k < 2.5 / d) return n * (k -= 2.25 / d) * k + .9375; return n * (k -= 2.625 / d) * k + .984375; },
    steps: n => k => Math.floor(k * n) / n,
    bezier: (x1, y1, x2, y2) => {                                  // cubic-bezier como no CSS / Graph Editor
      const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
      const X = s => ((ax * s + bx) * s + cx) * s, Y = s => ((ay * s + by) * s + cy) * s;
      return k => { let s = k; for (let i = 0; i < 8; i++) { const d = (X(s) - k); if (Math.abs(d) < 1e-5) break; const dx = (3 * ax * s + 2 * bx) * s + cx; if (Math.abs(dx) < 1e-6) break; s -= d / dx; } return Y(clamp(s)); };
    },
  };

  /* ---- mola analítica (amortecida): determinística, sem integrar frame a frame ---- */
  // retorna 0→1 com overshoot; zeta<1 oscila. t em segundos desde o início da mola.
  const spring = (t, { freq = 3, zeta = .45 } = {}) => {
    if (t <= 0) return 0;
    const w = freq * 2 * Math.PI, wd = w * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * w * t) * (Math.cos(wd * t) + (zeta * w / wd) * Math.sin(wd * t));
  };

  /* ---- aleatório com semente ---- */
  const rng = seed => { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };
  const hash = n => { const r = rng(Math.floor(n * 7919) + 1); return r(); };
  const noise1 = x => { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u) * 2 - 1; };
  const wiggle = (t, freq = 4, amp = 1, seed = 0) => (noise1(t * freq + seed * 31.7) + .5 * noise1(t * freq * 2 + seed * 17.3)) * amp / 1.5;
  // tremor que morre com o tempo — impacto: dispare no instante do golpe sonoro
  const shake = (t, t0, { dur = .5, amp = 18, freq = 28 } = {}) => {
    const k = 1 - prog(t, t0, t0 + dur); if (t < t0 || k <= 0) return [0, 0];
    return [wiggle(t, freq, amp * k * k, 1), wiggle(t, freq, amp * k * k, 2)];
  };

  /* ---- cor ---- */
  const hsl = (h, s, l, a = 1) => `hsla(${h},${s}%,${l}%,${a})`;
  const hex = c => { c = c.replace('#', ''); if (c.length === 3) c = c.split('').map(x => x + x).join(''); return c.match(/\w\w/g).map(x => parseInt(x, 16)); };
  const mix = (c1, c2, k) => { const a = hex(c1), b = hex(c2); return `rgb(${a.map((v, i) => Math.round(lerp(v, b[i], k))).join(',')})`; }; // só aceita #rgb/#rrggbb
  const rgba = (c, a) => { const [r, g, b] = hex(c); return `rgba(${r},${g},${b},${a})`; };

  /* ---- desenho ---- */
  // Trim Paths: desenha `path` (Path2D) de `from` a `to` (0..1). Precisa do comprimento total.
  const trim = (g, path, length, from, to) => {
    g.save(); const a = clamp(from) * length, b = clamp(to) * length;
    g.setLineDash([Math.max(b - a, 0), length * 2]); g.lineDashOffset = -a; g.stroke(path); g.restore();
  };
  // comprimento de uma polilinha
  const polyLen = pts => pts.reduce((s, p, i) => i ? s + Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) : 0, 0);
  const polyPath = (pts, close = false) => { const p = new Path2D(); pts.forEach((q, i) => i ? p.lineTo(q[0], q[1]) : p.moveTo(q[0], q[1])); if (close) p.closePath(); return p; };
  // reamostra uma polilinha em n pontos equidistantes (pré-requisito para morph limpo)
  const resample = (pts, n) => { const L = polyLen(pts), out = []; let acc = 0, j = 1; for (let i = 0; i < n; i++) { const d = L * i / (n - 1); while (j < pts.length - 1 && acc + Math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]) < d) { acc += Math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]); j++; } const a = pts[j - 1], b = pts[j], sl = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, k = clamp((d - acc) / sl); out.push([lerp(a[0], b[0], k), lerp(a[1], b[1], k)]); } return out; };
  const morph = (A, B, k) => A.map((p, i) => [lerp(p[0], B[i][0], k), lerp(p[1], B[i][1], k)]);
  // círculo / estrela / polígono como polilinhas já reamostráveis
  const circlePts = (cx, cy, r, n = 120) => Array.from({ length: n + 1 }, (_, i) => [cx + r * Math.cos(i / n * 6.2832 - 1.5708), cy + r * Math.sin(i / n * 6.2832 - 1.5708)]);
  const polyShape = (cx, cy, r, sides, rot = -Math.PI / 2) => { const p = Array.from({ length: sides }, (_, i) => [cx + r * Math.cos(rot + i / sides * 6.2832), cy + r * Math.sin(rot + i / sides * 6.2832)]); p.push(p[0]); return p; };

  // Texto cinético: revela por caractere com stagger. cada char: {x,y,alpha,scale,rot}.
  // fn(charProgress 0..1, index) devolve a pose; usa spring/ease que você escolher.
  const kinetic = (g, text, x, y, t, t0, { stagger = .035, dur = .5, ease = E.outBack, size = 120, font = 'Inter, Helvetica, Arial, sans-serif', weight = 800, align = 'center', rise = 40, color = '#fff', track = 0 } = {}) => {
    g.save(); g.font = `${weight} ${size}px ${font}`; g.textBaseline = 'alphabetic';
    const ws = [...text].map(c => g.measureText(c).width + track), total = ws.reduce((a, b) => a + b, 0);
    let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
    [...text].forEach((c, i) => {
      const k = prog(t, t0 + i * stagger, t0 + i * stagger + dur), e = ease(k);
      if (k > 0) { g.save(); g.globalAlpha = clamp(k * 3); g.translate(cx + ws[i] / 2, y + (1 - e) * rise); g.scale(.6 + .4 * e, .6 + .4 * e); g.fillStyle = color; g.textAlign = 'center'; g.fillText(c, 0, 0); g.restore(); }
      cx += ws[i];
    });
    g.restore(); return total;
  };
  // Máscara de revelação (track matte): clip retangular que abre; chame draw() dentro.
  const reveal = (g, x, y, w, h, k, draw, dir = 'right') => {
    g.save(); g.beginPath();
    if (dir === 'right') g.rect(x, y, w * k, h); else if (dir === 'up') g.rect(x, y + h * (1 - k), w, h * k); else g.rect(x + w * (1 - k), y, w * k, h);
    g.clip(); draw(); g.restore();
  };
  // Contador numérico animado
  const counter = (t, t0, t1, from, to, ease = E.outExpo, dec = 0) => (lerp(from, to, ease(prog(t, t0, t1)))).toFixed(dec);

  /* ---- partículas determinísticas: posição = f(semente, t). Sem simulação, então dá scrub ---- */
  const particles = (n, seed, spawn) => { const r = rng(seed); return Array.from({ length: n }, (_, i) => spawn(r, i)); };

  /* ---- câmera 2.5D: planos com `depth` (0 = longe, 1 = no plano da câmera) ---- */
  const cam = { x: 0, y: 0, zoom: 1, rot: 0 };
  const plane = (g, W, H, depth, fn) => { // paralaxe: planos próximos andam mais
    g.save(); g.translate(W / 2, H / 2); g.rotate(cam.rot * depth); const z = 1 + (cam.zoom - 1) * depth;
    g.scale(z, z); g.translate(-W / 2 - cam.x * depth, -H / 2 - cam.y * depth); fn(); g.restore();
  };

  /* ---- pós ---- */
  const vignette = (g, W, H, s = .55) => { const r = g.createRadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * .9); r.addColorStop(0, 'rgba(0,0,0,0)'); r.addColorStop(1, `rgba(0,0,0,${s})`); g.fillStyle = r; g.fillRect(0, 0, W, H); };
  let _grain = null;
  const grain = (g, W, H, t, amt = .06, fps = 24) => { // grão por frame-lógico (24fps) = textura de filme
    if (!_grain) { _grain = document.createElement('canvas'); _grain.width = 256; _grain.height = 256; }
    const c = _grain.getContext('2d'), id = c.createImageData(256, 256), r = rng(Math.floor(t * fps) + 1);
    for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255 * amt; }
    c.putImageData(id, 0, 0); g.save(); g.globalCompositeOperation = 'overlay'; g.fillStyle = g.createPattern(_grain, 'repeat'); g.fillRect(0, 0, W, H); g.restore();
  };
  // Glitch/aberração cromática: redesenha o canvas atual com canais deslocados.
  const chroma = (g, cv, W, H, amt) => {
    if (amt < .5) return; const snap = document.createElement('canvas'); snap.width = W; snap.height = H; snap.getContext('2d').drawImage(cv, 0, 0);
    g.save(); g.globalCompositeOperation = 'screen'; g.clearRect(0, 0, W, H); g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    [['#f00', -amt], ['#0f0', 0], ['#00f', amt]].forEach(([c, dx]) => { const tmp = document.createElement('canvas'); tmp.width = W; tmp.height = H; const tg = tmp.getContext('2d'); tg.drawImage(snap, 0, 0); tg.globalCompositeOperation = 'multiply'; tg.fillStyle = c; tg.fillRect(0, 0, W, H); g.drawImage(tmp, dx, 0); });
    g.restore();
  };
  const glow = (g, color, blur, fn) => { g.save(); g.shadowColor = color; g.shadowBlur = blur; fn(); g.restore(); };

  /* ---- timeline de cenas com transições ---- */
  // scenes: [{ start, end, draw(g, local, ctx) }]; `overlap` cria janela de transição entre cenas.
  // transition(g, ctx, k, drawA, drawB) pode ser customizada (wipe, whip, match cut...).
  const runScenes = (g, scenes, t, ctx) => {
    for (let i = 0; i < scenes.length; i++) {
      const s = scenes[i], tr = s.transitionOut; // { dur, fn(g, ctx, k, drawA, drawB) }
      const inTr = tr && t >= s.end - tr.dur && t < s.end && scenes[i + 1];
      if (inTr) {
        const k = prog(t, s.end - tr.dur, s.end), nx = scenes[i + 1];
        tr.fn(g, ctx, k, () => s.draw(g, t - s.start, ctx), () => nx.draw(g, t - nx.start + 0, ctx)); return;
      }
      if (t >= s.start && t < s.end - ((scenes[i - 1] && scenes[i - 1].transitionOut) ? 0 : 0)) {
        const prevTr = scenes[i - 1] && scenes[i - 1].transitionOut;
        if (prevTr && t < scenes[i - 1].end) continue; // coberto pela transição da cena anterior
        s.draw(g, t - s.start, ctx); return;
      }
    }
  };
  const T = { // transições prontas
    cut: { dur: 0, fn: (g, c, k, a, b) => b() },
    whip: dur => ({ dur, fn: (g, c, k, a, b) => { const e = E.inOutExpo(k), W = c.W; g.save(); g.translate(-W * e, 0); a(); g.restore(); g.save(); g.translate(W * (1 - e), 0); b(); g.restore(); } }),
    wipe: dur => ({ dur, fn: (g, c, k, a, b) => { a(); reveal(g, 0, 0, c.W, c.H, E.inOutCubic(k), b); } }),
    iris: (dur, cx, cy) => ({ dur, fn: (g, c, k, a, b) => { a(); g.save(); g.beginPath(); g.arc(cx ?? c.W / 2, cy ?? c.H / 2, Math.hypot(c.W, c.H) * E.inOutCubic(k), 0, 6.2832); g.clip(); b(); g.restore(); } }),
    dip: (dur, color = '#000') => ({ dur, fn: (g, c, k, a, b) => { if (k < .5) a(); else b(); g.fillStyle = color; g.globalAlpha = 1 - Math.abs(k - .5) * 2; g.fillRect(0, 0, c.W, c.H); g.globalAlpha = 1; } }),
  };

  /* ---- utilitários que quase todo projeto precisa ---- */
  // milhar em pt-BR: fmtInt(3200) -> "3.200"
  const fmtInt = n => Math.round(n).toLocaleString('pt-BR');
  // maior tamanho de fonte (≤ max) em que o texto cabe em maxW
  const fitText = (g, text, maxW, { font = 'Inter, Helvetica, Arial, sans-serif', weight = 800, max = 400 } = {}) => {
    g.save(); g.font = `${weight} 100px ${font}`; const w = g.measureText(text).width; g.restore(); return Math.min(max, 100 * maxW / w);
  };
  // halo de luz suave (sem bordas duras): use no lugar de retângulos/elipses com fill sólido
  const halo = (g, x, y, r, color = '#ffd9a0', a = 1, sx = 1, sy = 1) => {
    g.save(); g.translate(x, y); g.scale(sx, sy); const gr = g.createRadialGradient(0, 0, 0, 0, 0, r);
    gr.addColorStop(0, rgba(color, a)); gr.addColorStop(.35, rgba(color, a * .35)); gr.addColorStop(1, rgba(color, 0));
    g.fillStyle = gr; g.globalCompositeOperation = 'lighter'; g.beginPath(); g.arc(0, 0, r, 0, 6.2832); g.fill(); g.restore();
  };
  // Espera as fontes carregarem ANTES de medir texto ou marcar __ready (senão o layout usa a fonte errada).
  // Fontes locais: declare @font-face com arquivo ao lado do index.html e passe ex.: ['800 100px "MinhaFonte"']
  const fontsReady = async (specs = []) => { try { await Promise.all(specs.map(sp => document.fonts.load(sp))); await document.fonts.ready; } catch (e) { console.warn('fonts', e); } };
  // Zonas seguras (px) por formato: texto importante fica dentro delas
  const safe = (W, H) => H > W ? { top: Math.round(H * .12), bottom: Math.round(H * .22), side: Math.round(W * .07) }   // 9:16: UI de rede cobre topo e rodapé
                        : { top: Math.round(H * .07), bottom: Math.round(H * .07), side: Math.round(W * .06) };

  return { hex, rgba, fmtInt, fitText, halo, fontsReady, safe, clamp, lerp, map, prog, E, spring, rng, hash, noise1, wiggle, shake, hsl, mix, trim, polyLen, polyPath, resample, morph, circlePts, polyShape, kinetic, reveal, counter, particles, cam, plane, vignette, grain, chroma, glow, runScenes, T };
})();
