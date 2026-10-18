# Desenvolvimento / Development

## Testes / Tests
```bash
python ai-motion-director/scripts/registry.py check     # arquitetura
python -m unittest discover -s tests                    # tudo
python -m unittest discover -s tests -p "test_catalog.py" -v   # um arquivo
```
Requisitos extras só para render/áudio: `pip install -r requirements.txt`, Chromium do Playwright e `ffmpeg`. Sem eles, os testes que dependem disso são **pulados** (skip), não aprovados.

| Arquivo | Cobre |
|---|---|
| `test_structure.py` | frontmatter, arquivos obrigatórios, compatibilidade (CLIs antigas, exemplos), licença/README |
| `test_contracts.py` | validador, semântica do roteiro, regra de evidência, mensagens de erro |
| `test_catalog.py` | busca por facetas, nova técnica sem tocar no Core |
| `test_architecture.py` | registry; Core pequeno; módulo novo; ciclo; motor trocável; integração opcional ausente; handoff |
| `test_engines.py` | sonda de disponibilidade × verificação; seleção |
| `test_prompt_build.py` | shot-spec × perfil; avisos |
| `test_audio.py` | síntese determinística, sem clipping, onsets reais |
| `test_pipeline.py` | init/check/status/bundle (recusas) |
| `test_render_e2e.py` | render real ponta a ponta, relatório, inspeção, bundle, falha sem `__ready` |

Os 7 casos de arquitetura exigidos estão em `test_architecture.py`/`test_catalog.py`/`test_contracts.py`/`test_structure.py` (nova técnica sem tocar no Core; narrativa evolui sem mudar motor; motor trocável sem reescrever roteiro; integração opcional ausente não bloqueia; contratos rejeitam entrada inválida; executado ≠ recomendado; fluxos existentes continuam).

## Adicionar... / Adding...
- **Técnica:** objeto em `catalog/techniques/<arquivo>.json` (contrato `technique`; `narrative_intents`, `emotions`, `contexts`, `engines` válidos). `python .../catalog.py check`.
- **Motor:** `engines/<id>/engine.json` (contrato `engine-manifest`): `requirements`, limites, validação, `verification.state` (`planned`/`implemented-untested`/`verified`). `verified` exige testes reais em `evidence`. Motor externo = `external: true`, só plano.
- **Módulo:** `modules/<id>/module.json` (`core_contract` igual ao do Core, `consumes`/`produces` existentes, sem ciclo) e cite `` `id` `` em `SKILL.md`.
- **Perfil de prompt:** `prompt-profiles/<ferramenta>.json`; começa `verified: false` até testar na ferramenta real.
- **Estilo/perfil de formato:** `styles/*.json`, `profiles/*.json`.

## Convenções
Sem dependências para scripts de arquitetura; nunca afirmar execução sem evidência; Core ≤150 linhas e sem conteúdo especializado; mudanças em contratos do Core sobem `contract_version` e entram no `CHANGELOG.md`; tudo que é conhecimento mora em `references/`, dados em JSON.

## English summary
Run `python -m unittest discover -s tests` (render/audio tests skip without numpy, Pillow, Playwright+Chromium, ffmpeg). Add a technique by adding JSON to `catalog/techniques/`, an engine via `engines/<id>/engine.json`, a module via `modules/<id>/module.json` plus citing its id in the Core. Keep the Core ≤150 lines, never claim `executed`/`validated`/`verified` without evidence, and record Core-contract changes in `CHANGELOG.md`.
