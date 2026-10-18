# Exemplo 1 — Short vertical com um número (teste real da skill)

**Pedido do usuário:** "Vídeo vertical de uns 8 s para Reels da minha startup de finanças. Mensagem: 'brasileiros perdem em média R$ 3.200 por ano em taxas bancárias sem perceber'. Quero que dê um soco no estômago e que a pessoa lembre do número. Verde-escuro e amarelo. Sem trilha, mas quero som."

**Como a skill decidiu (e por quê)**
- Entender: nada essencial faltava ⇒ sem perguntas. Premissas declaradas: 1080×1920, 8 s, som ligado, sem logo (não fornecido), marca #0a2e1f + #ffd23f.
- Mensagem única: o número R$ 3.200. Emoção: soco no estômago (incômodo → clareza).
- Conceito: "sangramento invisível". Taxinhas minúsculas pingam cada vez mais rápido enquanto o contador sobe; **silêncio de 150 ms**; o total estala enorme.
- Técnicas escolhidas (e só estas): contador com `inExpo`/`outExpo`, fichas com stagger acelerado, shake+flash no estalo, tipografia cinética para o fecho. Descartado: partículas, glitch, parallax (não serviam à mensagem).

**Roteiro (resumo)**
| Tempo | Acontece | Som |
|---|---|---|
| 0–3,25 | contador sobe; fichas de taxa pipocam mais rápido; câmera empurra | tick por ficha + riser |
| 3,25–3,40 | silêncio, contador congela | silêncio |
| 3,40 | R$ 3.200 estala (escala 1,4→1, shake, flash) | impacto grave |
| 4,1 | "POR ANO" entra | pop |
| 5–8 | "em taxas bancárias que você nem percebe." respiro | cauda |

**Correção feita na avaliação:** na folha de contato as fichas se sobrepunham ao número e o número ocupava só 60% da largura ⇒ reposicionou fichas e aumentou a fonte (~90% da largura).
**Resultado verificado:** MP4 1080×1920, 24 fps, 8,0 s, com áudio. SFX sintetizados (rascunho). Render ≈ 0,69 s/frame.
**Lição de calibragem:** em formato vertical, o texto vai dentro de `M.safe(W,H)`; um número-herói precisa ocupar quase toda a largura útil.
