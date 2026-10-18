# Motores de animação e workflow de produção

Sumário: 1. Como escolher · 2. Canvas + motion-kit (padrão) · 3. Outros motores · 4. FFmpeg · 5. Workflow com IA generativa · 6. Ferramentas desktop · 7. Status de validação

A ferramenta é consequência da direção criativa. Escolha o motor mais simples que entregue o efeito pedido.

## 1. Como escolher
O registro real está em `engines/*/engine.json` (tipos de projeto, requisitos, entradas, saídas, limitações, validação e sondas de disponibilidade). Para escolher e ver o que existe AGORA neste ambiente:
```bash
python $SK/scripts/engines.py detect
python $SK/scripts/engines.py select --project-type vertical-short --need deterministic-seek,audio
```
A tabela abaixo é o resumo humano.

| Se o vídeo é… | Motor | Por quê |
|---|---|---|
| 2D gráfico: formas, tipografia, partículas, dados, logos, transições | **Canvas + motion-kit** | determinístico, rápido, sem dependências, roda aqui |
| Vetorial limpo e editável (ícones, personagem, infográfico) | **SVG** (+ GSAP ou SMIL) | formas semânticas com IDs, exporta SVG/Lottie |
| Muito texto/layout (UI, lower thirds, dashboards) | **HTML/CSS + GSAP** timeline pausada e seekable | layout de verdade, tipografia rica |
| 3D ou sombreamento | **Three.js** (WebGL) | precisa de `--capture jpeg/png` (screenshot) ou `preserveDrawingBuffer` |
| Matemática/ciência explicada | **Manim** (Python) | feito para isso; render próprio |
| Vídeo React com componentes/dados | **Remotion** | timelines declarativas, boa para templates em série |
| Montagem, corte, legendas, áudio, conversões | **FFmpeg** | operações sobre mídia já existente |
| Cinema/3D realista, compositing profundo | **Blender/C4D/AE/Houdini** | externo: entregue plano + passes, sem prometer render |

## 2. Canvas + motion-kit (padrão)
Arquivos: `assets/template/index.html`, `assets/template/motion-kit.js`.
Contrato com o renderizador:
```js
window.__meta  = { width, height, duration, fps };   // segundos
window.__canvas = document.querySelector('canvas');  // ativa captura rápida e sem perda
window.__seek = t => { /* desenha o estado exato no instante t, síncrono */ };
window.__sfx   = [{t:3.2,type:'impact'}];            // opcional: som sintetizado a partir dos mesmos tempos
window.__ready = true;                               // OBRIGATÓRIO, só depois de fontes/imagens carregarem
```
Regras para o código ser **seekable** (o render pula para qualquer t):
- sem `Math.random()`, `Date.now()`, `requestAnimationFrame` para animar, nem estado que dependa do frame anterior; use `M.rng(seed)` e funções de `t`
- partículas: posição = f(semente, t), nunca simulação passo a passo (se precisar de física, pré-calcule uma tabela determinística)
- fontes: use fontes do sistema ou `@font-face` com arquivo local ao lado do HTML; chame `await M.fontsReady(['800 100px "MinhaFonte"'])` **antes** de medir texto (`measureText`) e de marcar `__ready`; sem rede no render. Confira a fonte que realmente apareceu na folha de contato; se caiu numa genérica, o layout mudou
- números animados mudam de largura: ancore à esquerda ou meça a string final (`M.fitText` com o valor máximo) para o contador não "dançar" no centro
- cores em `M.mix`/`M.rgba`: use `#rgb` ou `#rrggbb`
- imagens/áudio: carregue localmente e só marque `window.__ready = true` depois do `onload`

Render (chame por caminho absoluto; em segundo plano se passar de ~1 min): `python $SK/scripts/render.py projeto/index.html saida.mp4 --fps 30 [--audio a.wav] [--blur 4] [--shutter 0.5] [--start s --end s] [--still t] [--crf 16]`.
- `--capture auto|canvas|png|jpeg`: com `window.__canvas` usa leitura direta do canvas (≈85 ms/frame 1080p, sem perda). Sem ele cai para screenshot JPEG (≈50 ms, qualidade 97); `png` via screenshot é lento (≈700 ms).
- `--blur N`: motion blur real por N sub-frames (obturador `--shutter` em fração do frame; 0,5 = 180°). Custa N× no tempo.
- Medido neste ambiente: 1080p, 30 fps, canvas ≈ 0,5 s/frame no total (9 s ≈ 2 min). Itere com `--fps 12` ou `--still`.
- Resolução: defina em `__meta`. 9:16 = 1080×1920; 1:1 = 1080×1080. Custo escala com os pixels.

Dicas de performance: evite `shadowBlur` grande em centenas de elementos por frame; `getImageData` é lento (use só em quadros-chave); pré-gere `Path2D` fora do `__seek`.

## 3. Outros motores (receitas curtas)
**SVG/GSAP**: construa uma `gsap.timeline({paused:true})`; em `__seek(t)` chame `tl.time(t)`; capture com `--capture jpeg`. IDs semânticos nos grupos (`#icone`, `#texto`) facilitam coreografia. Para desenhar contornos use `stroke-dasharray/offset` ou plugin DrawSVG; para morph de paths, mesma contagem de pontos.
**Three.js**: renderize em `__seek(t)` de forma síncrona (`renderer.render`), sem loop; câmera como função de `t`. Se `window.__canvas` for o canvas WebGL, crie o renderer com `preserveDrawingBuffer: true`. WebGL em Chromium headless usa renderização por software: teste a velocidade antes de planejar cenas pesadas.
**Remotion**: `npx create-video`, componentes com `useCurrentFrame()`; render `npx remotion render`. Exige Node e um Chromium; depende de baixar pacotes npm (normalmente permitido, confirme). Vale quando o vídeo é gerado em série a partir de dados.
**Manim**: `pip install manim` (precisa de Cairo/Pango e LaTeX para fórmulas; verifique antes). `manim -qh cena.py Cena`. Ótimo para explicações matemáticas.
**HTML puro para prévia**: abra `index.html?play` para ver em tempo real (só prévia; o render usa seek).

## 4. FFmpeg (montagem e acabamento)
```bash
# emendar trechos re-renderizados (mesmos parâmetros do render.py ⇒ concat sem recodificar)
#  python render.py p/index.html a.mp4 --start 0 --end 5 ; python render.py p/index.html b.mp4 --start 5 --end 8
#  (com window.__sfx o áudio de cada trecho é recortado do mesmo som; com --audio use o mesmo arquivo)
printf "file 'a.mp4'\nfile 'b.mp4'\n" > lista.txt && ffmpeg -f concat -safe 0 -i lista.txt -c copy final.mp4
# juntar vídeo + áudio, cortar no menor
ffmpeg -i v.mp4 -i a.wav -c:v copy -c:a aac -shortest out.mp4
# concatenar cenas com mesmo codec/resolução
ffmpeg -f concat -safe 0 -i lista.txt -c copy out.mp4
# speed ramp simples em vídeo real (2x depois 0.5x)
ffmpeg -i in.mp4 -filter_complex "[0:v]trim=0:2,setpts=PTS/2[a];[0:v]trim=2:4,setpts=2*(PTS-STARTPTS)[b];[a][b]concat=n=2:v=1:a=0" out.mp4
# GIF otimizado
ffmpeg -i in.mp4 -vf "fps=15,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" out.gif
# normalizar loudness para redes (~ -14 LUFS)
ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy out.mp4
# verticalizar 16:9 -> 9:16 com fundo desfocado
ffmpeg -i in.mp4 -filter_complex "[0:v]scale=1080:1920,boxblur=30[bg];[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" out.mp4
```
Exporte `yuv420p` + `+faststart` para compatibilidade (o `render.py` já faz).

## 5. Workflow com IA generativa (imagem, vídeo, áudio)
Quando o conceito pede texturas, cenários, personagens ou plano realista que código não entrega. Não presuma que o ambiente tem acesso a geradores: verifique as ferramentas/conectores disponíveis; sem eles, entregue os prompts prontos e o plano de integração, marcados como `generated`/`planned`, nunca como gerados.
Os princípios, o contrato `shot-spec`, os perfis de ferramenta e a montagem de prompts estão em `references/prompt-engineering.md` (módulo `prompt-engineering`). O motor `generative-ai-external` só descreve a integração; nada é executado pelo agente.

## 6. Ferramentas desktop (After Effects, Blender, Cinema 4D, Cavalry, DaVinci, Premiere)
Não rodam neste ambiente. Quando a direção pedir uma delas: entregue (1) lista de composições/camadas, (2) expressões ou scripts que você consiga escrever com segurança, (3) parâmetros de render/export, (4) plano de passes e composição. Marque tudo como "não executado". Exemplo de expressão AE (wiggle que morre): `amp=30*Math.max(0,1-(time-inPoint)/0.5); wiggle(25,amp)`.

## 7. Status de validação (o que foi realmente testado)
Fonte de verdade: o campo `verification` de cada `engine.json` e os testes em `tests/`. Resumo:
- Testado aqui: render Canvas→MP4 via Playwright+Chromium+FFmpeg, `inspect_video.py`, `audio_map.py`, `synth_sfx.py`, mux de áudio.
- Não testado aqui: SVG/GSAP, Three.js, Remotion, Manim, servidores MCP ou skills de terceiros citados em materiais do usuário (HyperFrames, VideoDB, SVGator MCP etc.). Se um destes for adotado, verifique a instalação e teste um exemplo mínimo antes de planejar em cima dele.
