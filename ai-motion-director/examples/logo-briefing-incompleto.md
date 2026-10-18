# Exemplo 2 — Logo com briefing incompleto (teste real da skill)

**Pedido do usuário:** "faz uma animação pro logo da minha empresa, a Lumen. tem que ficar moderna e impressionar. 16:9." (usuário indisponível para perguntas)

**Como a skill decidiu**
- Faltavam logo, identidade, duração, uso. Nenhum desses impede uma proposta ⇒ **premissas declaradas no topo e entrega**, sem questionário: lockup provisório (anel + palavra LUMEN), 6,4 s, som ligado, tom premium/tecnológico, fundo escuro com luz âmbar, uso como vinheta de abertura/encerramento.
- Mensagem única: "Lumen = a luz que nasce do escuro e revela" ⇒ a metáfora vem do **nome**, não de um efeito de catálogo.
- Conceito: uma faísca é puxada para si mesma, estoura, vira a marca (abertura de lente) e um feixe acende o nome letra a letra. Alternativa simples descartada: só fade-in do logo (não carrega a ideia).
- Técnicas: partículas determinísticas sugadas para o ponto (`inCubic`), shake leve e bloom no estalo, trim path para o anel, mola para o núcleo, glow, vinheta, grão.

**Roteiro (resumo)**
| Tempo | Imagem | Som |
|---|---|---|
| 0–1,5 | ponto de luz respira; partículas sugadas | drone + riser |
| 1,5 | estalo, onda de choque | silêncio ~0,1 s → impacto |
| 1,6–2,7 | anel se desenha; núcleo nasce com mola | shimmer |
| 2,75–3,9 | feixe varre, letras acendem quentes e esfriam | whoosh |
| 4,7–5,5 | brilho de passagem; respiro | shimmer |
| 6,05–6,4 | fade | cauda |

**Correções feitas na avaliação (folha de contato, 2 rodadas):** retângulos de luz com borda dura trocados por gradiente radial (`M.halo`); primeiro quadro quase vazio ⇒ ponto/halo maiores; ~0,3 s de trecho morto removido; brilho final vazando fora das letras.
**Resultado verificado:** MP4 1920×1080, 24 fps, 6,4 s, com áudio sintetizado. Render ≈ 65 s.
**Não validado:** sincronia fina imagem-som (confiada nos tempos compartilhados) e loudness; por isso o `--loudnorm` foi adicionado.
**Lição de calibragem:** com briefing incompleto, o melhor "diferencial" costuma estar no significado do nome ou do produto.
