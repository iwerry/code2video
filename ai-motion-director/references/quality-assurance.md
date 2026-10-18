# Avaliação e refinamento

Sumário: 1. Checagem técnica objetiva · 2. Matriz criativa · 3. Como registrar problemas · 4. Ciclo de refinamento · 5. Checklist final

## 1. Checagem técnica objetiva (sempre)
```bash
python scripts/inspect_video.py saida.mp4 --sheet folha.png --count 15
```
Depois **abra `folha.png` com Read** e examine: o frame de cada marco do roteiro mostra o que o roteiro promete? Confira também:
- duração, resolução, fps, presença de áudio batem com o briefing
- sem quadros pretos/congelados não intencionais (o script avisa; pausas dramáticas intencionais são esperadas)
- texto legível (tamanho, contraste, dentro da zona segura), sem cortes nas bordas
- impactos visuais alinhados ao áudio (olhe quadros ao redor do tempo do impacto: `--times 3.1,3.2,3.3`)
- erros no console da página (o `render.py` imprime avisos/erros)
- primeiro frame forte e último frame deliberado (fecho)
- em loops: primeiro e último frames compatíveis

Isso é verificação factual. Use-a antes de qualquer opinião estética.

## 2. Matriz criativa
Escala qualitativa explícita (para orientar decisões, não é métrica de audiência):
**1** compromete o objetivo · **2** fraco, precisa de correção · **3** funciona · **4** bom · **5** forte e específico.

| Critério | Pergunta |
|---|---|
| Clareza da mensagem | a ideia única se entende sem explicação? |
| Originalidade | poderia abrir qualquer outro vídeo do setor? |
| Coerência narrativa | cada cena prepara a próxima? |
| Progressão emocional | há curva (tensão→virada→clímax) ou é plano? |
| Função do motion | cada movimento tem motivo narrativo ou é decorativo? |
| Ritmo | há alternância entre intensidade e respiro? |
| Integração sonora | impactos e silêncios estão preparados? |
| Consistência visual | paleta, easing, tipografia, escala coerentes? |
| Legibilidade | texto/elementos são lidos no tempo e no tamanho? |
| Continuidade | transições e elementos persistentes fazem sentido? |
| Viabilidade e adequação | cabe nos recursos e na plataforma? |
| Cumprimento do briefing | cada critério de sucesso foi atendido? |

Não converta as notas em previsão de desempenho.

## 3. Como registrar problemas
Cada achado tem 5 campos:
```
Problema   : o anel termina de se desenhar quando o título já entrou (6.0 s vs 5.9 s)
Evidência  : frame 5.95 s na folha mostra o título cortando o anel
Impacto    : divide a atenção justo no momento da virada
Correção   : atrasar o título para 6.4 s ou encurtar o trim para 1.4 s
Prioridade : alta / média / baixa
```
"Está fraco" não é um achado. Se não houver evidência observável, diga que é hipótese.

## 4. Ciclo de refinamento
1. Liste problemas e priorize (alto impacto no objetivo primeiro)
2. Proponha a menor correção que resolve
3. Atualize só as partes afetadas (roteiro/código) e re-renderize o trecho: `--start 5 --end 8`
4. Revise de novo os frames do trecho **e** os vizinhos: a correção pode ter criado um problema novo (tempos que deslocam o resto, sincronia de som)
5. Pare quando os problemas de prioridade alta estiverem resolvidos; o que sobrar vai em "próximas melhorias"

Pergunte sempre: existe uma maneira mais simples, mais barata ou mais forte de atingir o mesmo efeito? Cortar costuma melhorar mais que acrescentar.

Para trabalho de alto risco (cliente final, campanha paga), peça uma revisão por um agente independente que não viu a produção, passando só o briefing, o roteiro e a folha de contato, para evitar que o autor avalie o próprio trabalho.

## 5. Checklist final
- [ ] vídeo renderizado e visto (folha de contato aberta)
- [ ] timecodes do roteiro coincidem com o que aparece
- [ ] soma das cenas = duração total
- [ ] áudio presente e sincronizado (se aplicável)
- [ ] premissas e limitações declaradas (o que foi testado, o que não foi)
- [ ] nenhuma promessa de viralização/métrica sem dados
- [ ] entrega enviada ao usuário com uma linha de contexto e um próximo passo possível
