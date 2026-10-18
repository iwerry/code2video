# Catálogo de motion: da intenção narrativa à técnica

> **Fonte de dados:** `catalog/techniques/*.json` (72 técnicas, contrato `technique`). Este arquivo é o guia de decisão em prosa; a busca estruturada é `python $SK/scripts/catalog.py search --intent hook --emotion tension --context short-social --feasible A` (também por categoria, tipo de movimento, complexidade e motor). Para adicionar técnica, solte um `.json` em `catalog/techniques/` e rode `catalog.py check`; nenhum outro arquivo precisa mudar. Quando houver divergência entre este texto e o JSON, vale o JSON.

Sumário: 1. Como usar · 2. Intenção → técnica · 3. Técnicas das 62 por viabilidade em código · 4. Combinações que funcionam · 5. Armadilhas

## 1. Como usar
Parta da **intenção** (coluna esquerda), nunca da lista de efeitos. Escolha 1 técnica principal e no máximo 2 de apoio por cena. Para cada técnica recomendada, registre: objetivo narrativo · efeito esperado · momento ideal · requisito técnico · complexidade · risco · alternativa mais simples.

As funções citadas (`M.*`) estão em `assets/template/motion-kit.js`.

## 2. Intenção → técnica → como fazer

| O espectador precisa… | Técnica | Implementação em código | Cuidado |
|---|---|---|---|
| **Parar de rolar** (hook) | Quebra de expectativa visual: movimento em frame 1, escala extrema, texto que contradiz a imagem | Cena já "em andamento" em t=0; `E.outExpo` na primeira entrada | O primeiro frame deve ser uma imagem forte *parada* (miniatura) |
| **Sentir tensão** | Aceleração + estreitamento: tremor crescente, câmera empurrando, partículas vibrando | `E.inExpo` sobre amplitude de `M.wiggle`; `M.cam.zoom` subindo | Silêncio ou riser sonoro; sem alívio visual antes do estalo |
| **Sentir impacto** | Hit: shake decrescente + flash de 3-6 frames + corte de silêncio | `M.shake(t,t0)`, flash alpha que cai em ~0,12 s | Impacto sem preparação não impacta; 1 por vídeo curto |
| **Entender uma transformação** | Morph de forma / match cut | `M.resample` + `M.morph`; match cut = mesma posição/escala/forma entre cenas | Reamostre as duas formas com o mesmo nº de pontos |
| **Acompanhar um processo** | Trim path / write-on, linha que conecta etapas | `M.trim(g,path,len,0,k)` com `E.inOutCubic` | Direção do traço = direção de leitura |
| **Ler uma frase no ritmo da fala** | Tipografia cinética sincronizada | `M.kinetic` com `stagger` ≈ ritmo; entrada de palavra no onset da fala | Legibilidade > estilo; ≥0,3 s/palavra |
| **Perceber escala/hierarquia** | Contador, barra que cresce, zoom de contexto | `M.counter` + `E.outExpo`; zoom out revelando tamanho | Números reais; animar o *delta*, não o total |
| **Sentir profundidade / mundo** | Parallax 2.5D, câmera virtual | `M.plane(g,W,H,depth,fn)` + `M.cam.x/zoom` com ease | Planos distantes se movem menos; evite rotação demais |
| **Sentir vida/peso** | Squash & stretch, antecipação, follow-through, mola | `M.spring`; escala `(1+s, 1-s)` na velocidade; recuo antes do avanço | Overshoot pequeno (zeta .4-.6) = vivo; grande = cartoon |
| **Sentir velocidade/mudança de cena** | Whip pan / slide com blur, speed ramp | `M.T.whip(dur)`; render com `--blur 4` | Blur real só com sub-frames (custa N× tempo) |
| **Sentir ordem após caos** | Partículas que convergem para forma | posições = `lerp(caos, alvo, E.outExpo)` sem simulação (scrub-safe) | Semente fixa; sem `Math.random` |
| **Perceber tecnologia / dados** | HUD/FUI, grade, scan, glitch controlado | linhas finas + `M.trim`; `M.chroma` em picos curtos | Glitch é tempero: 2-4 frames, em momentos de erro/ruptura |
| **Sentir calor/humano** | Textura, grão, vinheta, cor quente, movimento orgânico (wiggle baixo) | `M.grain`, `M.vignette`, `M.wiggle` suave | Grão por frame lógico (24 fps) imita filme |
| **Ser conduzido entre ideias** | Transição motivada: o objeto da cena A vira o cenário da B | iris em cima do objeto (`M.T.iris(dur,cx,cy)`), wipe seguindo o movimento | Se não há motivo, corte seco é melhor |
| **Reconhecer a marca** | Logo build, motion branding consistente | logo desenhado por trim → preenchimento com mola → respiro | Mantenha cor/ease/timing da marca em todo o vídeo |
| **Sentir ritmo / música** | Animação orientada a áudio | `audio.json` (onsets/rms): dispare cenas e pulsos nos onsets reais | Não sincronize tudo: acentue os tempos fortes |
| **Ter respiro / emoção** | Pausa: reduzir movimento, segurar o quadro | segurar valores finais por 0,5-1,2 s; só grão/respiração mínima | Pausa precisa ser intencional e curta |
| **Lembrar do fim** | Loop sem emenda / eco do hook | estado final = estado inicial em t=0 (`M.E.linear` em ciclos inteiros) | Em loops, todas as periódicas com períodos que dividem a duração |

## 3. As 62 técnicas do guia, por viabilidade em código

Legenda: **A** = nativo no motion-kit/Canvas · **B** = viável com esforço (SVG/GSAP/Three.js/FFmpeg) · **C** = ferramenta externa (AE/Blender/C4D/Houdini) — descreva o fluxo e gere o que for possível (storyboard, expressões, prompts) sem fingir que renderizou.

**Expert**
- A: Particle systems (1.000-5.000 pontos determinísticos), scripting/expression-driven (tudo aqui é código), morphing de vetores (`M.morph`)
- B: Procedural geometry nodes (Three.js procedural), camera projection (Three.js: textura projetada em planos), volumetric light (raios radiais em Canvas ou Three.js), morphing complexo de malhas 3D, displacement mapping (`getImageData` é lento: use em quadros-chave)
- C: Cel 3D/2D híbrido, rigging avançado/IK, rigid body/cloth, matchmoving, SSS, multipass/deep compositing, fluidos/fumaça/fogo (alternativa 2D: partículas com glow), optical flow (exige OpenCV, não verificado aqui) → planeje em Blender/C4D/AE; no código, entregue o plano e os passes esperados

**Avançado**
- A: Secondary motion/overlap (offset de fase entre partes), kinetic typography 2D, luma matte/track matte (`clip`/`globalCompositeOperation`), seamless loop, glitch/chroma (`M.chroma`), parallax multiplano (`M.plane`), shape deformers (wiggle/zigzag/pucker via funções de contorno), audio spectrum (`audio_map.py`), text animators com range selector (`M.kinetic` com stagger/ease), transições vetoriais customizadas, HUD/FUI
- B: Isometria (projeção matemática `x=(a-b)·cos30°, y=(a+b)·sin30°-z`), NPR/toon (Three.js outline), tipografia cinética espacial 3D
- C: Rotoscopia e pintura quadro a quadro (precisa de vídeo + máscara; trabalho manual)

**Médio**
- A: Easing/graph editor (`E.bezier`), squash & stretch, anticipation/follow-through, camera moves 2D, trim paths, write-on, drop shadows (`shadowBlur`), parenting (transform hierárquico com `g.save/translate/rotate`), cloners (laço com offset por índice), motion blur (`--blur`), glow (`M.glow`), morph simples, color grading simples (overlay/curvas), tipografia cinética básica (precisa dos tempos reais da fala para sincronizar)
- B: Speed ramp/time remapping (reamostrar tempo com `E.inOutCubic` aplicado a `t`; em vídeo real, FFmpeg `setpts`), chroma key (FFmpeg `colorkey`/`chromakey`)

**Básico**
- A: tudo (keyframes, transform, fade, anchor point, máscaras, slides, gradientes, wiggle, lower thirds, backgrounds em loop, stingers, pop-in de texto, vinheta)

**Técnicas adicionais do briefing do projeto**: match cut (A), whip pan (A), speed ramp (B), animação de interface/dados (A), infográfico animado (A/B com SVG), produto 3D (C ou Three.js), composição live-action + CGI (C; ou FFmpeg overlay para camadas simples), morphing de cenários (B, via IA generativa + crossfade/flow, ver `engines.md`), integração de assets de IA (B).

## 4. Combinações que funcionam (receitas)
- **Lançamento tech (10-15 s)**: caos de partículas → estalo (shake+flash+riser) → forma que se desenha (trim) → logo com mola → tagline cinética. Poucas cores, um acento.
- **Dado que surpreende**: contexto minimalista → silêncio → número que sobe com `outExpo` → zoom-out mostrando a escala → frase de leitura em 2 s.
- **Emocional/social**: câmera lenta e orgânica (parallax baixo, grão, cor quente) → pausa → um movimento decidido na virada → texto curto, respirado.
- **Explicativo**: objeto-guia que persiste entre cenas (continuidade), transição por transformação, uma ideia por cena, recapitulação visual no fim.
- **Short vertical**: hook em <1 s, cortes a cada 1-2,5 s, texto grande na zona segura, loop que reencaixa no frame 1.
- **Musical**: elementos pulsando no `rms`, cortes e impactos nos `onsets`; acalme nos breakdowns para o drop ter contraste.

## 5. Armadilhas
- Todos os elementos se movendo ao mesmo tempo → nada é lido. Escalone (stagger) e hierarquize.
- Ease padrão em tudo → movimento sem caráter. Escolha por intenção (seção 2).
- Glitch/shake/flash como tempero constante → vira ruído e perde força.
- Parallax ou zoom sem motivo → enjoo e distração.
- Efeito caro onde um corte seco funcionaria. Cite a alternativa simples e escolha conscientemente.
- Esquecer que técnicas "C" não rodam aqui: não prometa render delas.
