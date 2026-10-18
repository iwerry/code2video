#!/usr/bin/env python3
"""Validação de contratos entre módulos (JSON Schema, subconjunto) + checagens semânticas.

Sem dependências externas (só biblioteca padrão), para rodar em qualquer ambiente de agente.

CLI:
  python contracts.py validate <contrato> <arquivo.json>     # ex.: validate script roteiro.json
  python contracts.py list                                   # contratos disponíveis
  python contracts.py check-dir <pasta>                      # valida *.json de um projeto pelo nome
                                                              # (brief.json, script.json, plan.json, ...)

Como biblioteca:
  from contracts import validate, validate_file, ContractError
  validate("script", dict_)  -> lista de erros (vazia = válido)

Subconjunto suportado: type, enum, const, required, properties, additionalProperties(bool),
items, minItems, maxItems, minLength, minimum, maximum, pattern, if/then, $ref (local e arquivo).
Não é um validador completo de JSON Schema: o que não é suportado é ignorado, nunca aceito com
sentido diferente. Os contratos deste projeto só usam o subconjunto acima (testado em tests/).

Regra transversal (semântica): `status` ∈ recommended < planned < generated < executed < validated.
executed/validated EXIGEM `evidence` não vazio. Assim nenhum módulo pode afirmar que executou ou
validou algo sem apontar a prova (frame, log, teste, arquivo).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_DIR = os.path.join(os.path.dirname(HERE), "contracts")

STATUS_ORDER = ["recommended", "planned", "generated", "executed", "validated"]

# nome do arquivo do projeto -> contrato
PROJECT_FILES = {
    "brief.json": "creative-brief",
    "script.json": "script",
    "plan.json": "production-plan",
    "recommendations.json": "technique-recommendation",
    "render-report.json": "execution-report",
    "qa-technical.json": "qa-report",
    "qa-creative.json": "qa-report",
}


class ContractError(Exception):
    pass


def schema_path(name):
    return os.path.join(CONTRACTS_DIR, f"{name}.schema.json")


def list_contracts():
    return sorted(f[: -len(".schema.json")] for f in os.listdir(CONTRACTS_DIR) if f.endswith(".schema.json"))


def load_schema(name):
    p = schema_path(name)
    if not os.path.isfile(p):
        raise ContractError(f"contrato desconhecido: '{name}'. Disponíveis: {', '.join(list_contracts())}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _type_ok(v, t):
    if t == "string": return isinstance(v, str)
    if t == "boolean": return isinstance(v, bool)
    if t == "integer": return isinstance(v, int) and not isinstance(v, bool)
    if t == "number": return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "array": return isinstance(v, list)
    if t == "object": return isinstance(v, dict)
    if t == "null": return v is None
    return True


def _resolve(ref, root, base_name):
    """$ref: '#/definitions/x' (no mesmo arquivo) ou 'arquivo.schema.json#/definitions/x'."""
    file_part, _, ptr = ref.partition("#")
    if file_part:
        name = file_part[: -len(".schema.json")] if file_part.endswith(".schema.json") else file_part
        doc, base = load_schema(name), name
    else:
        doc, base = root, base_name
    node = doc
    for part in [p for p in ptr.split("/") if p]:
        node = node[part]
    return node, doc, base


def _walk(value, schema, root, base, path, errs):
    if "$ref" in schema:
        node, doc, b = _resolve(schema["$ref"], root, base)
        _walk(value, node, doc, b, path, errs)
        return
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in types):
            errs.append(f"{path or '$'}: esperado {'/'.join(types)}, recebi {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path or '$'}: deve ser {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path or '$'}: valor {value!r} inválido; permitidos: {', '.join(map(str, schema['enum']))}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errs.append(f"{path or '$'}: texto vazio ou curto demais (mín. {schema['minLength']})")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path or '$'}: '{value}' não casa com o padrão {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path or '$'}: {value} < mínimo {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path or '$'}: {value} > máximo {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append(f"{path or '$'}: precisa de ao menos {schema['minItems']} item(ns)")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path or '$'}: no máximo {schema['maxItems']} item(ns)")
        if "items" in schema:
            for i, it in enumerate(value):
                _walk(it, schema["items"], root, base, f"{path}[{i}]", errs)
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{path or '$'}: campo obrigatório ausente: '{k}'")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _walk(v, props[k], root, base, f"{path}.{k}" if path else k, errs)
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path or '$'}: campo desconhecido '{k}' (permitidos: {', '.join(props)})")
    if "if" in schema and "then" in schema:
        probe = []
        _walk(value, schema["if"], root, base, path, probe)
        if not probe:
            _walk(value, schema["then"], root, base, path, errs)


# ---------- checagens semânticas (o que schema não expressa) ----------
def _sem_status_evidence(inst, errs, path="$"):
    """executed/validated exigem evidência, em qualquer nível do documento."""
    if isinstance(inst, dict):
        st = inst.get("status")
        if st in ("executed", "validated") and not inst.get("evidence"):
            errs.append(f"{path}: status '{st}' exige 'evidence' (frame, log, teste ou arquivo que prove). "
                        f"Sem prova, use 'generated' ou 'planned'.")
        for k, v in inst.items():
            _sem_status_evidence(v, errs, f"{path}.{k}")
    elif isinstance(inst, list):
        for i, v in enumerate(inst):
            _sem_status_evidence(v, errs, f"{path}[{i}]")


def _sem_script(inst, errs):
    """Consistência temporal: cenas contíguas e soma = duração total (tolerância de 1 frame)."""
    fps = inst.get("fps", 30)
    tol = 1.0 / fps + 1e-6
    total = inst.get("duration_s")
    scenes = inst.get("scenes", [])
    prev_end = 0.0
    for i, sc in enumerate(scenes):
        s, e = sc.get("start_s"), sc.get("end_s")
        if s is None or e is None:
            continue
        if e <= s:
            errs.append(f"scenes[{i}] ('{sc.get('name', i)}'): fim ({e}) deve ser maior que início ({s})")
        expected = prev_end - sc.get("overlap_s", 0)   # transição com sobreposição declarada em overlap_s
        if abs(s - expected) > tol:
            errs.append(f"scenes[{i}] ('{sc.get('name', i)}'): começa em {s}s mas deveria começar em {expected:.3f}s "
                        f"(fim da anterior {prev_end}s - overlap_s {sc.get('overlap_s', 0)}); lacuna ou sobreposição não declarada")
        prev_end = e
        for c in sc.get("cues", []):
            if not (s - tol <= c.get("t", s) <= e + tol):
                errs.append(f"scenes[{i}] cue '{c.get('type')}' em t={c.get('t')}s fora da cena [{s}, {e}]")
    if scenes and total is not None and abs(prev_end - total) > tol:
        errs.append(f"soma das cenas termina em {prev_end}s mas duration_s = {total}s")
    for i, sc in enumerate(scenes):
        sc_dur = sc.get("end_s", 0) - sc.get("start_s", 0)
        for tm in sc.get("motions", []):
            if tm.get("duration_s", 0) > sc_dur + tol:
                errs.append(f"scenes[{i}]: movimento '{tm.get('what')}' dura {tm['duration_s']}s e a cena só {sc_dur:.2f}s")


def _sem_manifest_module(inst, errs):
    if inst.get("id") in inst.get("depends_on", []):
        errs.append("módulo não pode depender de si mesmo")


SEMANTIC = {"script": [_sem_script], "module-manifest": [_sem_manifest_module]}


def validate(name, instance):
    """Retorna lista de mensagens de erro; vazia = válido."""
    schema = load_schema(name)
    errs = []
    _walk(instance, schema, schema, name, "", errs)
    if not errs:  # semântica só faz sentido em estrutura válida
        _sem_status_evidence(instance, errs)
        for fn in SEMANTIC.get(name, []):
            fn(instance, errs)
    return errs


def validate_file(name, path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"{path}: JSON inválido (linha {e.lineno}, coluna {e.colno}): {e.msg}"]
    except OSError as e:
        return [f"{path}: não foi possível ler ({e.strerror})"]
    return validate(name, data)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "list":
        print("\n".join(list_contracts()))
        return 0
    if cmd == "validate" and len(argv) == 3:
        try:
            errs = validate_file(argv[1], argv[2])
        except ContractError as e:
            print(f"erro: {e}", file=sys.stderr)
            return 2
        if errs:
            print(f"INVÁLIDO ({argv[1]}): {len(errs)} problema(s)")
            for e in errs:
                print("  -", e)
            return 1
        print(f"ok: {argv[2]} cumpre o contrato '{argv[1]}'")
        return 0
    if cmd == "check-dir" and len(argv) == 2:
        bad, found = 0, 0
        for fname, contract in PROJECT_FILES.items():
            p = os.path.join(argv[1], fname)
            if os.path.isfile(p):
                found += 1
                errs = validate_file(contract, p)
                print(f"{'ok  ' if not errs else 'FAIL'} {fname} ({contract})")
                for e in errs:
                    print("      -", e)
                bad += bool(errs)
        if not found:
            print("nenhum artefato de projeto encontrado (brief.json, script.json, ...)")
        return 1 if bad else 0
    print("uso: contracts.py validate <contrato> <arquivo> | list | check-dir <pasta>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
