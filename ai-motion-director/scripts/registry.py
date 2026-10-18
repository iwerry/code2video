#!/usr/bin/env python3
"""Registro de módulos e motores: descobre manifestos, valida contratos e garante a arquitetura.

CLI:
  python registry.py list                 # módulos e motores, versão e estado de verificação
  python registry.py show <id>            # manifesto completo
  python registry.py graph                # dependências entre módulos
  python registry.py check [--skill-dir DIR]   # valida TUDO (retorna código ≠ 0 se algo quebrar)

O que 'check' garante (cada item é um teste de arquitetura, não só de formato):
  1. core.json existe, é compatível e o ponto de entrada (SKILL.md) continua pequeno
  2. cada module.json cumpre o contrato module-manifest; id == nome da pasta
  3. docs/data/scripts declarados existem
  4. consumes/produces apontam para contratos que existem
  5. depends_on aponta para módulos existentes e não há ciclos
  6. core_contract do módulo == contract_version do Core
  7. o Core cita todos os módulos pelo id (ele precisa conhecer os contratos, não o conteúdo)
  8. engines, técnicas, perfis, estilos e prompt-profiles cumprem seus contratos
Adicionar um módulo/motor/técnica = adicionar uma pasta/arquivo; nada no Core precisa mudar,
exceto citar o id do módulo novo em SKILL.md (item 7 avisa).
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import contracts  # noqa: E402

DEFAULT_ROOT = os.path.dirname(HERE)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def discover(root):
    mods = {}
    for p in sorted(glob.glob(os.path.join(root, "modules", "*", "module.json"))):
        d = load_json(p)
        mods[d.get("id", os.path.basename(os.path.dirname(p)))] = (p, d)
    engines = {}
    for p in sorted(glob.glob(os.path.join(root, "engines", "*", "engine.json"))):
        d = load_json(p)
        engines[d.get("id", os.path.basename(os.path.dirname(p)))] = (p, d)
    return mods, engines


def find_cycle(graph):
    state, stack = {}, []

    def visit(n):
        state[n] = 1
        stack.append(n)
        for m in graph.get(n, []):
            if state.get(m) == 1:
                return stack[stack.index(m):] + [m]
            if state.get(m) is None:
                c = visit(m)
                if c:
                    return c
        state[n] = 2
        stack.pop()
        return None

    for n in graph:
        if state.get(n) is None:
            c = visit(n)
            if c:
                return c
    return None


def check(root):
    errs = []
    rel = lambda p: os.path.relpath(p, root)

    # 1. Core
    core_p = os.path.join(root, "core", "core.json")
    core = None
    if not os.path.isfile(core_p):
        errs.append("core/core.json ausente")
    else:
        core = load_json(core_p)
        entry = os.path.join(root, core["entry"])
        if not os.path.isfile(entry):
            errs.append(f"ponto de entrada {core['entry']} ausente")
        else:
            n = sum(1 for _ in open(entry, encoding="utf-8"))
            if n > core.get("max_entry_lines", 150):
                errs.append(f"{core['entry']} tem {n} linhas (máx. {core['max_entry_lines']}): o Core deve ficar pequeno; "
                            f"mova conteúdo especializado para um módulo")

    mods, engines = discover(root)

    for mid, (p, d) in mods.items():
        # 2. contrato do manifesto
        for e in contracts.validate("module-manifest", d):
            errs.append(f"{rel(p)}: {e}")
        if mid != os.path.basename(os.path.dirname(p)):
            errs.append(f"{rel(p)}: id '{mid}' difere do nome da pasta")
        # 3. arquivos declarados
        for key in ("docs", "data", "scripts"):
            for f in d.get(key, []):
                if not os.path.exists(os.path.join(root, f)):
                    errs.append(f"{rel(p)}: {key} aponta para '{f}', que não existe")
        repo_root = os.path.dirname(root)
        has_tests = os.path.isdir(os.path.join(repo_root, "tests"))  # pacote .skill não leva tests/: não cobrar lá
        for ev in d.get("verification", {}).get("evidence", []):
            if d["verification"]["state"] == "verified" and has_tests \
               and not os.path.exists(os.path.join(repo_root, ev)) and not os.path.exists(os.path.join(root, ev)):
                errs.append(f"{rel(p)}: evidência de verificação '{ev}' não encontrada (procurei na raiz do repositório e da skill)")
        # 4. contratos citados existem
        for key in ("consumes", "produces"):
            for c in d.get(key, []):
                if not os.path.isfile(contracts.schema_path(c)):
                    errs.append(f"{rel(p)}: {key} cita contrato inexistente '{c}'")
        # 5. dependências existem
        for dep in d.get("depends_on", []):
            if dep not in mods:
                errs.append(f"{rel(p)}: depends_on cita módulo inexistente '{dep}'")
        # 6. compatibilidade com o Core
        if core and d.get("core_contract") != core["contract_version"]:
            errs.append(f"{rel(p)}: core_contract={d.get('core_contract')} mas o Core está na versão {core['contract_version']}")
        if d.get("verification", {}).get("state") == "verified" and not d["verification"].get("evidence"):
            errs.append(f"{rel(p)}: estado 'verified' exige evidências (testes) em verification.evidence")

    cyc = find_cycle({m: d.get("depends_on", []) for m, (_, d) in mods.items()})
    if cyc:
        errs.append("dependência circular entre módulos: " + " → ".join(cyc))

    # 7. o Core conhece os módulos
    if core and os.path.isfile(os.path.join(root, core["entry"])):
        text = open(os.path.join(root, core["entry"]), encoding="utf-8").read()
        for mid in mods:
            if f"`{mid}`" not in text:
                errs.append(f"{core['entry']} não cita o módulo `{mid}` entre crases (o Core precisa conhecer o contrato de cada módulo)")

    # 8. motores e dados
    for eid, (p, d) in engines.items():
        for e in contracts.validate("engine-manifest", d):
            errs.append(f"{rel(p)}: {e}")
        if eid != os.path.basename(os.path.dirname(p)):
            errs.append(f"{rel(p)}: id '{eid}' difere do nome da pasta")
    for pattern, contract in (("profiles/*.json", "profile"), ("styles/*.json", "style-alias"),
                              ("prompt-profiles/*.json", "prompt-profile")):
        for p in sorted(glob.glob(os.path.join(root, pattern))):
            if os.path.basename(p).startswith("_"):
                continue
            for e in contracts.validate_file(contract, p):
                errs.append(f"{rel(p)}: {e}")
    try:
        import catalog
        errs += [f"catalog: {e}" for e in catalog.check(root)]
        known = set(engines)
        for t in catalog.load_all(root):
            for en in t.get("engines", []):
                if en not in known:
                    errs.append(f"catalog: técnica '{t['id']}' cita motor inexistente '{en}'")
    except ImportError:
        errs.append("scripts/catalog.py ausente")
    return errs, mods, engines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "show", "graph", "check"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--skill-dir", default=DEFAULT_ROOT)
    a = ap.parse_args(argv)
    root = os.path.abspath(a.skill_dir)

    if a.cmd == "check":
        errs, mods, engines = check(root)
        if errs:
            print(f"ARQUITETURA INVÁLIDA: {len(errs)} problema(s)")
            for e in errs:
                print("  -", e)
            return 1
        print(f"ok: {len(mods)} módulos, {len(engines)} motores; contratos, referências, dependências e Core consistentes")
        return 0

    mods, engines = discover(root)
    if a.cmd == "list":
        print("MÓDULOS")
        for mid, (_, d) in mods.items():
            print(f"  {mid:30s} v{d['version']:7s} [{d['verification']['state']}]  {d['kind']}")
        print("MOTORES")
        for eid, (_, d) in engines.items():
            ext = " (externo)" if d.get("external") else ""
            print(f"  {eid:30s} v{d['version']:7s} [{d['verification']['state']}]{ext}")
        return 0
    if a.cmd == "graph":
        for mid, (_, d) in mods.items():
            print(f"{mid} -> {', '.join(d['depends_on']) or '(nenhuma)'}   | consome {d['consumes']} | produz {d['produces']}")
        return 0
    if a.cmd == "show":
        hit = mods.get(a.id) or engines.get(a.id)
        if not hit:
            print(f"id desconhecido: {a.id}", file=sys.stderr)
            return 2
        print(json.dumps(hit[1], ensure_ascii=False, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
