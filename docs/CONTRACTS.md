# Contratos entre módulos / Contracts between modules

Fonte de verdade: `ai-motion-director/contracts/*.schema.json`. Validador: `scripts/contracts.py` (stdlib).

| Contrato | Produzido por | Consumido por | Para quê |
|---|---|---|---|
| `creative-brief` | creative-intelligence | narrative, motion-graphics | objetivo, público, emoção, mensagem única, formato |
| `script` | narrative-intelligence, audio-rhythm (cues) | engines, motion-graphics, automation | cenas com timecodes, movimentos, cues de som |
| `technique-recommendation` | motion-graphics-intelligence | engines | técnicas escolhidas pela função, com risco e alternativa simples |
| `production-plan` | production-engines | automation | motor, perfil, passos; só plano |
| `execution-report` | production-automation (render.py/pipeline.py) | quality-assurance | o que de fato rodou |
| `qa-report` | quality-assurance | Core | achados com evidência; `kind` = `technical` ou `creative` |
| `shot-spec` / `prompt-profile` | prompt-engineering | — | decisão criativa × limites da ferramenta |
| `engine-manifest`, `module-manifest`, `profile`, `style-alias`, `technique` | dados da arquitetura | registry | validação da arquitetura |
| `handoff` | Core | outra Skill | delegação com `expected_output` e `fallback` |

## Regras
1. **Versionado:** módulos declaram `core_contract`; deve ser igual a `core/core.json → contract_version`.
2. **Níveis de afirmação:** `recommended < planned < generated < executed < validated`. Distinguem recomendação, plano, código gerado, resultado executado e validação.
3. **Evidência:** `executed`/`validated` em qualquer nível do documento exigem `evidence` não vazio. Sem prova o validador rejeita com mensagem explicando o que usar.
4. **Rejeição clara:** erros trazem caminho (`scenes[1].end_s`), valor e permitidos. Campos desconhecidos são rejeitados onde `additionalProperties: false`.
5. **Semântica do `script`:** cenas contíguas (exceto `overlap_s` declarado), soma = `duration_s` (tolerância de 1 frame), cues dentro da cena, movimentos cabendo na cena.
6. **Técnico × criativo:** `inspect_video.py` gera `qa-report` técnico (nunca `validated`); o criativo é escrito por quem viu a folha de contato.

## Uso
```bash
python ai-motion-director/scripts/contracts.py list
python ai-motion-director/scripts/contracts.py validate <contrato> <arquivo.json>
python ai-motion-director/scripts/contracts.py check-dir <pasta-do-projeto>
```
Subconjunto de JSON Schema suportado: `type, enum, const, required, properties, additionalProperties(bool), items, minItems, maxItems, minLength, minimum, maximum, pattern, if/then, $ref`. Palavras-chave fora disso são ignoradas (nunca aceitas com outro sentido).

## English summary
Contracts are versioned JSON Schemas validated by a stdlib-only validator. Every artifact carries a `status` (`recommended < planned < generated < executed < validated`); `executed`/`validated` require `evidence`. Errors name the path, value and allowed values. Technical and creative QA are separate reports. Cross-Skill delegation uses the `handoff` contract with a mandatory-by-convention `fallback` (see `references/interop.md`).
