# Roteiro, storyboard e consistência temporal

Sumário: 1. Roteiro por cena · 2. Storyboard textual · 3. Regras de tempo · 4. Modelo completo · 5. Projetos pequenos

## 1. Roteiro por cena
Um roteiro é uma sequência causal, não uma lista de imagens bonitas: cada cena prepara a seguinte. Para cada cena, inclua o que se aplicar:

```
CENA n · 00:03.2–00:06.2 (3.0 s) · "ORDEM"
Objetivo narrativo : mostrar que o caos virou clareza
Emoção             : alívio → confiança
Visual / ação      : pontos convergem num anel que se desenha; núcleo nasce com mola
Enquadramento      : plano frontal, anel centrado ligeiramente acima do meio (y=40%)
Câmera             : empurrada lenta (zoom 1.00→1.06) que solta no estalo
Movimento gráfico  : converge outExpo 0.9 s; trim inOutCubic 1.8 s; mola freq 2.6 zeta .38
Transição de saída : contínua (o anel sobe para abrir espaço ao título)
Texto na tela      : —
Locução            : —
Áudio              : impacto em 3.2; whoosh em 3.6; silêncio de 80 ms antes do impacto
Paleta/luz         : fundo #0b0d12; acento #ff5a36; brilho suave no traço
Técnica            : Canvas · partículas determinísticas + trim path + spring
Recursos           : —
Continuidade       : anel mantém posição e raio na cena seguinte
Prompt de IA       : — (n/a)
```

## 2. Storyboard textual
Cada cena deve permitir "ver" o quadro sem interpretação vaga. Especifique:
- **Composição**: regra de terços/centro, simetria, espaço negativo
- **Posição e escala** dos elementos principais (em % da tela ou px)
- **Direção do movimento** (esquerda→direita, de fora para dentro) e coerência com a leitura
- **Profundidade**: primeiro plano / plano médio / fundo
- **Mudança visual** entre o primeiro e o último quadro da cena
- **Continuidade** com a cena seguinte (match de posição, forma, cor, movimento)
- **Zona segura** para texto e UI da plataforma (≥5-10% nas bordas; em 9:16 evite as faixas superior/inferior onde a UI cobre)

Para vídeos longos ou complexos, gere também quadros-chave reais (`render.py --still t`) e mostre ao usuário antes do render completo.

## 3. Regras de tempo (verifique antes de entregar)
1. A soma das durações das cenas = duração total (tolerância de 1 frame; escolha precisão: 0,1 s ou frames).
2. Cada cena começa onde a anterior termina; transições com sobreposição dizem isso explicitamente.
3. Nenhum movimento exige mais tempo do que a cena permite. Referência: entrada de elemento 0,3-0,6 s; stagger 30-60 ms/caractere; mola assenta em ~1 s; trim de contorno 1-2 s; leitura de texto ≥ 0,3 s/palavra + 0,4 s.
4. Impactos visuais e sonoros no mesmo timecode. Anticipação 3-8 frames antes do impacto.
5. Respiro antes e depois do clímax (0,5-1,2 s).
6. Em loops: último frame ≈ primeiro frame.

Dica: escreva as marcas de tempo como constantes no código (`const IMPACT = 3.2`) e use as mesmas no roteiro e na síntese de som, assim a sincronia não deriva.

## 4. Modelo completo de entrega (vídeo completo)
A. Diagnóstico criativo · B. Conceito recomendado · C. Justificativa · D. Estrutura narrativa · E. Roteiro com timecodes · F. Storyboard por cena · G. Direção de motion graphics · H. Direção de fotografia/arte · I. Plano de áudio e ritmo · J. Prompts de geração (se houver IA) · K. Workflow de produção · L. Plano de pós · M. Avaliação crítica e melhorias.

## 5. Projetos pequenos
Combine B+C+D, entregue roteiro curto em tabela (tempo · o que acontece · movimento · som) e vá direto ao render. Se o usuário só pediu a ideia, não renderize; ofereça.
