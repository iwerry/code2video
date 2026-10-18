# Changelog

Formato inspirado em Keep a Changelog. / Format inspired by Keep a Changelog.

## [1.0.0] — arquitetura modular / modular architecture

### Compatibilidade / Compatibility
- **Preservados / Preserved:** nome (`ai-motion-director`), frontmatter e gatilho de `SKILL.md`; `render.py`, `inspect_video.py`, `audio_map.py`, `synth_sfx.py` com a mesma CLI (os novos `--report` são opcionais; sem eles a saída é a de antes); `assets/template/` e os exemplos em Markdown; o fluxo `Entender → … → Aprimorar`.
- Contrato do Core: `contract_version = 1`. Mudar o Core exige subir essa versão e atualizar os `core_contract` dos módulos (`registry.py check` cobra).

### Adicionado / Added
- **Core pequeno** (`SKILL.md`, 82 linhas, limite 150 verificado) + `core/core.json`.
- **8 módulos** independentes (`modules/*/module.json`): creative-intelligence, narrative-intelligence, motion-graphics-intelligence, prompt-engineering, production-engines, audio-rhythm, quality-assurance, production-automation.
- **15 contratos JSON** (`contracts/`) + `scripts/contracts.py` (validador de subconjunto de JSON Schema só com stdlib, mais checagens semânticas: cenas contíguas, soma = duração, `executed`/`validated` exigem `evidence`).
- **Níveis de afirmação:** `recommended < planned < generated < executed < validated`.
- **Catálogo pesquisável** de 72 técnicas como dados (`catalog/techniques/*.json`, busca por intenção, emoção, categoria, tipo de movimento, contexto, complexidade, viabilidade, motor) — `scripts/catalog.py`.
- **8 motores declarados** (`engines/*/engine.json`) com requisitos, limites, validação e `verification`; `scripts/engines.py` sonda disponibilidade real e seleciona motor. "Disponível ≠ testado".
- **Prompt engineering:** `shot-spec` (decisão criativa) separado de `prompt-profiles/` (limites da ferramenta); `scripts/prompt_build.py`.
- **Automação:** `scripts/pipeline.py` (`init/check/render/inspect/bundle/status`) com relatórios rastreáveis; `bundle` recusa empacotar sem render real.
- **Interoperabilidade:** envelope `handoff` com fallback; `references/interop.md`.
- **QA separada:** relatório técnico (medidas, nunca `validated`) × criativo.
- **Testes:** 83 testes em `tests/` (stdlib `unittest`), incluindo prova dos 7 casos de arquitetura e render ponta a ponta real.
- `README.md` bilíngue, `docs/CONTRACTS.md`, `docs/DEVELOPMENT.md`, `requirements.txt`, `.github/workflows/ci.yml` (não verificado no GitHub).

### Alterado / Changed
- `render.py`: `--report`, `window.__ready` estritamente `=== true`, áudio a partir de `window.__sfx`.
- `inspect_video.py`: `--report`; sem `BrokenPipeError` com `| head`.
- `synth_sfx.py`: funções `render_events`/`write_wav` reutilizáveis.
- `references/engines.md` e `motion-catalog.md` apontam para os dados (fonte de verdade) em vez de duplicá-los.

### Limitações conhecidas / Known limitations
- Motores `svg-gsap`, `threejs`, `remotion`, `manim` estão `implemented-untested`; `desktop-dcc-external` e `generative-ai-external` são só plano.
- `prompt-profiles` são genéricos e não verificados contra nenhuma ferramenta real.
- O workflow de CI nunca rodou no GitHub.
- Avaliação criativa depende de alguém olhar a folha de contato; nenhum script a faz.

## [0.1.0]
- Primeira versão da skill (fluxo, referências, template Canvas, render/inspeção/áudio).
