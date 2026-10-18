# Automação de produção

Sumário: 1. O que a automação faz e não faz · 2. Layout do projeto · 3. Comandos · 4. Render: detalhes e custo · 5. Registros rastreáveis · 6. Reprocessar trechos · 7. Falhas comuns

## 1. O que a automação faz (e não faz)
`scripts/pipeline.py` coordena os scripts existentes (render, inspeção, áudio) e **registra o que realmente executou**. Ele não decide criativamente (isso é do Core e dos módulos de conhecimento), não agenda tarefas e não publica em plataformas. Princípio: nada é "renderizado", "inspecionado" ou "validado" sem um registro com evidência.

Níveis de afirmação (contrato `common#status`): `recommended` < `planned` < `generated` < `executed` < `validated`. `executed` e `validated` exigem `evidence` (arquivo, frame, log, teste); `contracts.py` rejeita sem ela.

## 2. Layout do projeto
```
projeto/
  project.json                       perfil, estilo, título
  brief.json script.json plan.json   artefatos dos módulos (contratos em contracts/)
  index.html motion-kit.js           o vídeo (motor canvas-motion-kit)
  out/render-report.json             resultado da renderização (fato)
  out/qa-technical.json out/folha.png    validação técnica (medidas + folha de contato)
  qa-creative.json                   avaliação criativa (quem olhou a folha escreve)
  deliver/                           pacote final com MANIFEST.json (sha256)
```

## 3. Comandos (use `$SK` = pasta da skill, caminho absoluto)
```bash
python $SK/scripts/pipeline.py init projeto --profile vertical-short --style punchy-social --duration 8
python $SK/scripts/pipeline.py check projeto          # contratos + coerência META×perfil×roteiro
python $SK/scripts/pipeline.py render projeto --still 3.4        # quadro-chave
python $SK/scripts/pipeline.py render projeto --loudnorm         # vídeo completo (rode em segundo plano)
python $SK/scripts/pipeline.py inspect projeto        # validação técnica; depois ABRA out/folha.png
python $SK/scripts/pipeline.py bundle projeto         # recusa se não houve render bem-sucedido
python $SK/scripts/pipeline.py status projeto
```
Perfis disponíveis em `profiles/`, estilos em `styles/`. Os scripts de baixo nível (`render.py`, `inspect_video.py`, `audio_map.py`, `synth_sfx.py`) continuam utilizáveis diretamente, com as mesmas opções de sempre.

## 4. Render: detalhes e custo
- Contrato com a página: `window.__meta`, `window.__seek(t)`, `window.__ready = true` (obrigatório), `window.__canvas` (captura rápida), `window.__sfx` (som a partir dos mesmos tempos do visual).
- Toda animação é função pura de `t` (sem `Math.random`, `Date.now`, estado acumulado). `pipeline.py check` avisa se encontrar esses usos fora de comentários.
- Custo medido (1080p, canvas): ≈ 0,4-0,7 s/frame. 8-9 s a 24-30 fps ≈ 1-2,5 min. `--blur N` multiplica por N. **Rode em segundo plano** (`nohup … > render.log 2>&1 &`): comandos longos em primeiro plano estouram o limite de tempo.
- Para iterar: `--fps 12`, `--start/--end`, `--still`.
- fps padrão vem de `META.fps`; fonte: espere `M.fontsReady([...])` antes de marcar `__ready`.

## 5. Registros rastreáveis
- `out/render-report.json` (contrato `execution-report`): comando, início, duração, ok, frames, fps, resolução, captura, áudio, saídas, mensagens/erros da página. Escrito mesmo quando o render falha (`ok: false` exige `errors`).
- `out/qa-technical.json` (contrato `qa-report`, `kind: technical`): duração, resolução, fps, codec, áudio, quadros amostrados e alertas. **Nunca** vem como `validated`: medir não é aprovar.
- `qa-creative.json` (`kind: creative`): matriz de `references/quality-assurance.md`, escrita por quem olhou a folha.
- Validação técnica e avaliação criativa são registradas **separadamente** de propósito.

## 6. Reprocessar trechos
`render --start S --end E` gera um trecho; para emendar, use a receita de concat em `references/engines.md` §4. Para vídeos curtos, re-renderizar tudo costuma ser mais simples e menos sujeito a erro de emenda.

## 7. Falhas comuns
| Sintoma | Causa | Ação |
|---|---|---|
| "A página não definiu window.__ready" | fontes/imagens ainda carregando ou esquecido | marcar `__ready` após `M.fontsReady`/`onload` |
| render dá timeout no terminal | comando longo em primeiro plano | rodar em segundo plano e ler o log |
| texto cai em fonte genérica | fonte não carregada antes de medir | `await M.fontsReady([...])` e conferir na folha |
| `bundle` recusa | não há render com `ok: true` | renderizar de verdade antes |
