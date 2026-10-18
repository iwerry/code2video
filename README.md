# AI Motion Director (CODE2VIDEO)

[Português (Brasil)](#português-brasil) · [English](#english)

---

# Português (Brasil)

## 1. Apresentação
**AI Motion Director** é uma *Skill* de agente (Claude) que atua como diretor criativo e engenheiro de motion: parte do objetivo, da emoção e da narrativa, escolhe técnicas de motion graphics pela **função** que cumprem e produz o vídeo **por código** (Canvas/HTML renderizado frame a frame em MP4), conferindo o resultado.

- **Problema que resolve:** vídeos feitos por programação costumam virar vitrine de efeitos soltos, sem narrativa, sem som sincronizado e sem checagem. Aqui a técnica é consequência da intenção, e o que foi planejado, gerado, executado e validado é registrado separadamente.
- **Diferenciais:** Core pequeno + módulos independentes; catálogo de 72 técnicas pesquisável por intenção/emoção/viabilidade; contratos JSON validáveis entre módulos; render determinístico com som sincronizado (`window.__sfx`); regra de evidência (`executed`/`validated` exigem prova); honestidade sobre o que está disponível × testado.
- **Público e casos de uso:** criadores, designers de motion, devs e agentes que precisam de vinhetas, logos animados, shorts/reels verticais, tipografia cinética, visualização de dados animada, roteiros com storyboard, revisão de roteiros/vídeos existentes.

## 2. Funcionalidades
**Implementado e verificado** (testes em `tests/`, ver §8): validação de contratos; registro/arquitetura (`registry.py check`); catálogo de técnicas e busca; seleção de motores com sonda de disponibilidade; montagem de prompts de geração; síntese de SFX determinística e mapa de áudio; pipeline `init/check/render/inspect/bundle/status`; render Canvas → MP4 (Playwright + Chromium + FFmpeg) com relatório; inspeção técnica de vídeo.

**Implementado, não testado:** motores `svg-gsap`, `threejs`, `remotion`, `manim` (receitas e manifestos; sem render de teste), `creative-intelligence` (conhecimento sem teste automatizável do conteúdo).

**Planejado / apenas plano:** After Effects/Blender/Cinema 4D, geradores de IA externos (o projeto só gera *prompts* e plano; não chama essas ferramentas).

## 3. Arquitetura
O **Core** (`ai-motion-director/SKILL.md`, ≤150 linhas, verificado) decide a abordagem, coordena o ciclo, escolhe técnica e motor pela viabilidade real, resolve conflitos, checa coerência e avalia. Ele **não** carrega catálogo, regras de storytelling, prompts por ferramenta nem implementação de motores: conhece apenas os **contratos** e quando chamar cada módulo.

| Módulo | Papel | Contrato (consome → produz) |
|---|---|---|
| `creative-intelligence` | briefing, estratégia, diferencial | → `creative-brief` |
| `narrative-intelligence` | narrativa, emoção, roteiro, storyboard | `creative-brief` → `script` |
| `motion-graphics-intelligence` | catálogo de técnicas por função | brief+script → `technique-recommendation` |
| `prompt-engineering` | prompts para IA generativa | `shot-spec` → prompt |
| `production-engines` | motores, disponibilidade, seleção | script+profile → `production-plan` |
| `audio-rhythm` | som e ritmo com dados reais | `script` → `script` (cues) |
| `quality-assurance` | avaliação técnica × criativa | `execution-report` → `qa-report` |
| `production-automation` | preparar, renderizar, inspecionar, reunir | `production-plan` → `execution-report` |

Fluxo de decisão: `INTENT → PROFILE → MODULES → STYLE ALIAS → ENGINE → SHOT PARAMETERS → FINAL PROMPT/RENDER`.

```
.
├── LICENSE                      # MIT
├── README.md  CHANGELOG.md  requirements.txt
├── ai-motion-director.skill     # pacote instalável da Skill
├── .github/workflows/ci.yml     # CI (não verificado no GitHub)
├── docs/                        # CONTRACTS.md, DEVELOPMENT.md
├── tests/                       # 83 testes (unittest, stdlib)
└── ai-motion-director/          # a Skill
    ├── SKILL.md                 # Core
    ├── core/core.json
    ├── modules/<id>/module.json # 8 módulos
    ├── contracts/*.schema.json  # 15 contratos
    ├── catalog/techniques/*.json# 72 técnicas, 12 arquivos
    ├── engines/<id>/engine.json # 8 motores
    ├── profiles/  styles/  prompt-profiles/
    ├── references/              # documentação por módulo
    ├── scripts/                 # contracts, registry, catalog, engines, prompt_build,
    │                            # pipeline, render, inspect_video, audio_map, synth_sfx
    ├── assets/template/         # index.html + motion-kit.js
    └── examples/
```

**Evolução independente:** nova técnica = soltar um `.json` em `catalog/techniques/`; novo motor = pasta em `engines/`; novo módulo = pasta em `modules/` + citar o id no Core; nova ferramenta de prompt = `prompt-profiles/*.json`. Os testes provam que nada disso exige alterar o Core (exceto citar o id de um módulo novo) nem reescrever o roteiro.

**Outras Skills:** não se presume chamada nativa entre Skills. A colaboração usa o envelope `handoff` (tarefa, entradas, contrato esperado, **fallback**, status) descrito em `ai-motion-director/references/interop.md`. Integração indisponível nunca bloqueia o fluxo básico (testado com o contrato; nenhuma Skill de terceiros foi integrada de fato).

## 4. Fluxo de trabalho
`Entender → Conceber → Comparar → Estruturar → Planejar → Produzir → Avaliar → Aprimorar`

1. **Entender:** objetivo, público, emoção, "a única coisa a lembrar", formato (`creative-brief`).
2. **Conceber/Comparar:** ideia central com metáfora visual; até 3 caminhos com trade-offs.
3. **Estruturar:** arquitetura emocional, roteiro com timecodes e som (`script`, validado: cenas contíguas, soma = duração).
4. **Planejar:** técnicas pela função (`catalog.py search`), motor pela viabilidade (`engines.py select`).
5. **Produzir:** `pipeline.py init` → código (animação = função pura de `t`) → `render` → `render-report.json`.
6. **Avaliar:** `inspect` (técnico) + olhar `out/folha.png` (criativo, registrado à parte).
7. **Aprimorar:** correção localizada, novo render e nova checagem.

## 5. Instalação e requisitos
- Python ≥ 3.9 (testado em 3.13). Arquitetura/contratos/catálogo/motores/prompts: **só biblioteca padrão**.
- Para renderizar e inspecionar: `pip install -r requirements.txt` (numpy, pillow, playwright), `python -m playwright install chromium` (ou `CHROMIUM_PATH`), e `ffmpeg`/`ffprobe` no PATH.
- Como Skill: instale `ai-motion-director.skill` no seu cliente Claude (ou copie a pasta `ai-motion-director/`).

Verificar a instalação:
```bash
SK=ai-motion-director
python $SK/scripts/registry.py check          # arquitetura inteira
python $SK/scripts/engines.py detect          # o que existe de fato neste ambiente
python -m unittest discover -s tests          # testes (os de render pulam sem a pilha)
```

## 6. Exemplos de utilização
Pedidos ao agente:
- *"Crie uma animação de logotipo de 5 s para a marca Lumen"* — exemplo: `examples/logo-lumen/`, `examples/logo-briefing-incompleto.md`.
- *"Faça um short vertical de 15 s sobre um dado que surpreende"* — `examples/short-vertical-dado.md` e `.../short-vertical-dado/*.json`.
- *"Desenvolva um roteiro com storyboard para…"* — modelos em `references/script-storyboard.md`.
- *"Que técnicas de motion usar para um hook de impacto?"* — `catalog.py search`.
- *"Revise esse vídeo/roteiro"* — modo Creative Audit.

Comandos:
```bash
SK=ai-motion-director
python $SK/scripts/catalog.py search --intent impact --context short-social --feasible A
python $SK/scripts/engines.py select --project-type vertical-short
python $SK/scripts/contracts.py validate script $SK/examples/short-vertical-dado/script.json
python $SK/scripts/pipeline.py init meu-video --profile vertical-short --style tech-premium-dark
python $SK/scripts/pipeline.py render meu-video --still 3      # um frame, rápido
python $SK/scripts/pipeline.py render meu-video                # vídeo completo (≈0,5 s/frame em 1080p)
python $SK/scripts/pipeline.py inspect meu-video               # medidas + out/folha.png
python $SK/scripts/pipeline.py bundle meu-video                # deliver/ + MANIFEST.json
python $SK/scripts/prompt_build.py --list
```

## 7. Desenvolvimento e contribuição
Guia completo: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md); contratos: [`docs/CONTRACTS.md`](docs/CONTRACTS.md).
- **Técnica:** adicione um objeto ao array de um `.json` em `catalog/techniques/`; rode `catalog.py check`.
- **Motor:** `engines/<id>/engine.json` com requisitos, limites, validação e `verification` honesto.
- **Módulo:** `modules/<id>/module.json` (+ docs/dados/scripts declarados), cite `` `id` `` no Core.
- **Convenções:** não registre `executed`/`validated` sem `evidence`; não marque `verified` sem teste em `evidence`; o Core fica ≤150 linhas; não crie dependência circular entre módulos; mudar um contrato do Core = subir `contract_version` e documentar no CHANGELOG.
- **Testes:** `python -m unittest discover -s tests`.

## 8. Limitações e estado do projeto
| Categoria | Itens |
|---|---|
| Implementado e **verificado** (83 testes executados localmente) | contratos, registro/arquitetura, catálogo, engines (detecção/seleção), prompt_build, áudio (síntese e mapa), pipeline, render Canvas ponta a ponta, inspeção |
| Implementado, **não testado** | `svg-gsap`, `threejs`, `remotion`, `manim`; conteúdo de `creative-intelligence` |
| **Integrações opcionais** | motores externos, Skills de terceiros via `handoff`, geradores de IA, After Effects/Blender (todos só plano) |
| **Planejadas** | testes reais dos motores acima; perfis de prompt verificados por ferramenta; execução do CI no GitHub |
| **Limitações conhecidas** | `prompt-profiles` genéricos e não verificados; render lento (≈0,4–0,7 s/frame em 1080p); `bpm_estimate` é heurística; avaliação criativa depende de alguém olhar a folha; o CI (`.github/workflows/ci.yml`) nunca rodou no GitHub; nenhuma promessa de viralização ou conversão |

Licença: **MIT** (arquivo `LICENSE`).

## 9. Créditos
**Desenvolvimento / Development: Daniel Rodrigues**

---

# English

## 1. Overview
**AI Motion Director** is an agent *Skill* (Claude) that works as a creative director and motion engineer: it starts from goal, emotion and narrative, picks motion-graphics techniques by the **function** they serve, and produces the video **in code** (Canvas/HTML rendered frame by frame to MP4), checking the result.

- **Problem it solves:** programmatic videos tend to become a showcase of unrelated effects, with no narrative, no synced sound and no review. Here technique follows intent, and what was planned, generated, executed and validated is recorded separately.
- **Differentiators:** small Core + independent modules; a 72-technique catalog searchable by intent/emotion/feasibility; validated JSON contracts between modules; deterministic rendering with synced sound (`window.__sfx`); evidence rule (`executed`/`validated` require proof); honesty about available × tested.
- **Audience and use cases:** creators, motion designers, developers and agents needing idents, animated logos, vertical shorts/reels, kinetic typography, animated data viz, scripts with storyboards, review of existing scripts/videos.

## 2. Features
**Implemented and verified** (tests in `tests/`, see §8): contract validation; registry/architecture (`registry.py check`); technique catalog and search; engine selection with availability probes; generation-prompt builder; deterministic SFX synthesis and audio map; `init/check/render/inspect/bundle/status` pipeline; Canvas → MP4 render (Playwright + Chromium + FFmpeg) with report; technical video inspection.

**Implemented, untested:** engines `svg-gsap`, `threejs`, `remotion`, `manim` (recipes and manifests, no test render); `creative-intelligence` (knowledge content with no automatable test).

**Planned / plan-only:** After Effects/Blender/Cinema 4D and external AI generators (the project produces *prompts* and plans only; it does not call those tools).

## 3. Architecture
The **Core** (`ai-motion-director/SKILL.md`, ≤150 lines, enforced) decides the approach, coordinates the cycle, picks technique and engine by real feasibility, resolves conflicts, checks coherence and evaluates. It does **not** hold the catalog, storytelling rules, per-tool prompts or engine implementations: it only knows the **contracts** and when to call each module.

| Module | Role | Contract (consumes → produces) |
|---|---|---|
| `creative-intelligence` | briefing, strategy, differentiator | → `creative-brief` |
| `narrative-intelligence` | narrative, emotion, script, storyboard | `creative-brief` → `script` |
| `motion-graphics-intelligence` | technique catalog by function | brief+script → `technique-recommendation` |
| `prompt-engineering` | prompts for generative AI | `shot-spec` → prompt |
| `production-engines` | engines, availability, selection | script+profile → `production-plan` |
| `audio-rhythm` | sound and rhythm from real data | `script` → `script` (cues) |
| `quality-assurance` | technical × creative review | `execution-report` → `qa-report` |
| `production-automation` | prepare, render, inspect, bundle | `production-plan` → `execution-report` |

Decision flow: `INTENT → PROFILE → MODULES → STYLE ALIAS → ENGINE → SHOT PARAMETERS → FINAL PROMPT/RENDER`.

The directory tree is shown in the Portuguese section above (identical; paths are not translated).

**Independent evolution:** new technique = drop a `.json` in `catalog/techniques/`; new engine = a folder in `engines/`; new module = a folder in `modules/` + cite its id in the Core; new prompt tool = `prompt-profiles/*.json`. Tests demonstrate none of this requires changing the Core (other than citing a new module's id) nor rewriting the script.

**Other Skills:** native cross-Skill calls are not assumed. Collaboration uses the `handoff` envelope (task, inputs, expected contract, **fallback**, status) described in `ai-motion-director/references/interop.md`. An unavailable integration never blocks the basic flow (tested at the contract level; no third-party Skill is actually integrated).

## 4. Workflow
`Understand → Conceive → Compare → Structure → Plan → Produce → Evaluate → Improve` (code names: `Entender → Conceber → Comparar → Estruturar → Planejar → Produzir → Avaliar → Aprimorar`)

1. **Understand:** goal, audience, emotion, "the one thing to remember", format (`creative-brief`).
2. **Conceive/Compare:** central idea with a visual metaphor; up to 3 paths with trade-offs.
3. **Structure:** emotional architecture, timecoded script and sound (`script`, validated: contiguous scenes, sum = duration).
4. **Plan:** techniques by function (`catalog.py search`), engine by feasibility (`engines.py select`).
5. **Produce:** `pipeline.py init` → code (animation = pure function of `t`) → `render` → `render-report.json`.
6. **Evaluate:** `inspect` (technical) + look at `out/folha.png` (creative, recorded separately).
7. **Improve:** localized fix, re-render, re-check.

## 5. Installation and requirements
- Python ≥ 3.9 (tested on 3.13). Architecture/contracts/catalog/engines/prompts: **standard library only**.
- To render and inspect: `pip install -r requirements.txt` (numpy, pillow, playwright), `python -m playwright install chromium` (or `CHROMIUM_PATH`), and `ffmpeg`/`ffprobe` on PATH.
- As a Skill: install `ai-motion-director.skill` in your Claude client (or copy the `ai-motion-director/` folder).

Verify the installation:
```bash
SK=ai-motion-director
python $SK/scripts/registry.py check          # whole architecture
python $SK/scripts/engines.py detect          # what actually exists in this environment
python -m unittest discover -s tests          # tests (render tests skip without the stack)
```

## 6. Usage examples
Requests to the agent:
- *"Create a 5 s logo animation for the brand Lumen"* — see `examples/logo-lumen/`, `examples/logo-briefing-incompleto.md`.
- *"Make a 15 s vertical short about a surprising number"* — `examples/short-vertical-dado.md` and `.../short-vertical-dado/*.json`.
- *"Write a script with storyboard for…"* — templates in `references/script-storyboard.md`.
- *"Which motion techniques for an impact hook?"* — `catalog.py search`.
- *"Review this video/script"* — Creative Audit mode.

Commands:
```bash
SK=ai-motion-director
python $SK/scripts/catalog.py search --intent impact --context short-social --feasible A
python $SK/scripts/engines.py select --project-type vertical-short
python $SK/scripts/contracts.py validate script $SK/examples/short-vertical-dado/script.json
python $SK/scripts/pipeline.py init my-video --profile vertical-short --style tech-premium-dark
python $SK/scripts/pipeline.py render my-video --still 3       # one frame, fast
python $SK/scripts/pipeline.py render my-video                 # full video (~0.5 s/frame at 1080p)
python $SK/scripts/pipeline.py inspect my-video                # measurements + out/folha.png
python $SK/scripts/pipeline.py bundle my-video                 # deliver/ + MANIFEST.json
python $SK/scripts/prompt_build.py --list
```

## 7. Development and contributing
Full guide: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md); contracts: [`docs/CONTRACTS.md`](docs/CONTRACTS.md).
- **Technique:** add an object to the array of a `.json` in `catalog/techniques/`; run `catalog.py check`.
- **Engine:** `engines/<id>/engine.json` with requirements, limits, validation and an honest `verification`.
- **Module:** `modules/<id>/module.json` (+ declared docs/data/scripts), cite `` `id` `` in the Core.
- **Conventions:** never record `executed`/`validated` without `evidence`; never mark `verified` without a test in `evidence`; Core stays ≤150 lines; no circular module dependencies; changing a Core contract = bump `contract_version` and note it in the CHANGELOG.
- **Tests:** `python -m unittest discover -s tests`.

## 8. Limitations and project status
| Category | Items |
|---|---|
| Implemented and **verified** (83 tests run locally) | contracts, registry/architecture, catalog, engines (detection/selection), prompt_build, audio (synthesis and map), pipeline, end-to-end Canvas render, inspection |
| Implemented, **untested** | `svg-gsap`, `threejs`, `remotion`, `manim`; `creative-intelligence` content |
| **Optional integrations** | external engines, third-party Skills via `handoff`, AI generators, After Effects/Blender (all plan-only) |
| **Planned** | real tests for the engines above; tool-verified prompt profiles; running CI on GitHub |
| **Known limitations** | generic, unverified `prompt-profiles`; slow render (~0.4–0.7 s/frame at 1080p); `bpm_estimate` is a heuristic; creative review needs someone to look at the contact sheet; CI (`.github/workflows/ci.yml`) has never run on GitHub; no promise of virality or conversion |

License: **MIT** (`LICENSE` file).

## 9. Credits
**Desenvolvimento / Development: Daniel Rodrigues**
