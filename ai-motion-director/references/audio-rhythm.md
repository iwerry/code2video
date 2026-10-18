# Áudio e ritmo

Sumário: 1. Princípios · 2. Dados reais da música · 3. Sem trilha: sound design sintetizado · 4. Padrões de sincronia · 5. Mixagem e entrega

## 1. Princípios
O som decide metade do impacto. Planeje junto com a imagem: o momento visual forte é também o momento sonoro forte.
- **Silêncio antes do impacto** (50-150 ms ou mais) torna o impacto maior.
- **Transientes** (ataque do som) ligam ao frame exato do movimento; coloque o visual 0-1 frame antes do pico do som.
- **Risers** sobem tensão antes de um estalo; **drones** sustentam atmosfera; **whooshes** acompanham movimento rápido; **ticks/pops** pontuam texto e UI.
- **Voz sempre inteligível**: abaixe música/SFX sob a locução (ducking, ~-8 a -12 dB).
- Em plataformas sociais muita gente assiste sem som: a história precisa funcionar sem áudio (texto/legenda/imagem).

## 2. Dados reais da música
Não invente BPM nem marcações. Se o usuário fornecer a faixa:
```bash
python scripts/audio_map.py faixa.mp3 --out audio.json --fps 30
```
Saída: `duration`, `rms[]` (energia 0-1 por frame), `onsets[]` (tempos em s), `bpm_estimate` (heurística; informe como estimativa e confirme com o usuário/estrutura da música).
No HTML, embuta o JSON (`const AUDIO = {...}`) e use:
```js
const e = AUDIO.rms[Math.min(AUDIO.rms.length-1, Math.floor(t*AUDIO.fps))]; // reatividade
const hit = AUDIO.onsets.filter(o => o<=t && t-o<.25);                       // pulso nos onsets
```
Escolha os onsets importantes (seções, drops) em vez de reagir a todos: pulsar em tudo vira ruído. Para estrutura (intro/verso/refrão), peça ao usuário ou escute os saltos de `rms` e confirme.

Sem música definida: descreva as características desejadas (andamento, intensidade, timbres, onde silencia) e deixe a escolha da faixa para depois.

## 3. Sem trilha: sound design sintetizado
`scripts/synth_sfx.py` gera SFX básicos (impact, riser, whoosh, tick, pop, drone, shimmer) a partir de uma lista de eventos com tempos exatos:
```json
[{"t":0,"type":"riser","dur":3.2,"gain":0.6},{"t":3.2,"type":"impact","gain":0.9}]
```
```bash
python scripts/synth_sfx.py --events eventos.json --duration 9 --out sfx.wav
python scripts/render.py projeto/index.html saida.mp4 --audio sfx.wav
```
É um rascunho funcional para travar a sincronia e dar vida ao protótipo, não um master profissional: avise o usuário. Para acabamento, sugira biblioteca de SFX/trilha licenciada ou geração por IA de áudio (se disponível), mantendo os mesmos timecodes.

## 4. Padrões de sincronia
| Momento | Imagem | Som |
|---|---|---|
| Tensão | zoom/tremor crescentes | riser + filtro abrindo; música tira graves |
| Impacto | shake curto + flash 3-6 frames | impacto grave + silêncio imediatamente antes |
| Revelação | movimento decidido, foco no objeto | acorde/shimmer, riser cai |
| Texto | pop-in por palavra | tick leve, só nas palavras-chave |
| Transição rápida | whip/wipe com blur | whoosh com a mesma duração da transição |
| Pausa dramática | reduzir movimento | cortar música por 0,3-0,8 s |
| Fecho | logo/frase estável | cauda de reverb, resolução harmônica |

## 5. Mixagem e entrega
- Normalize para redes em torno de -14 LUFS e pico real ≤ -1 dBTP: `ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy out.mp4`.
- Evite clipping (o `synth_sfx.py` já normaliza se passar de 0,95).
- Verifique com `inspect_video.py` se o MP4 final tem trilha de áudio e a duração bate com a imagem.
- Declare o que foi feito: "SFX sintetizados (rascunho)" ou "trilha fornecida pelo usuário".
