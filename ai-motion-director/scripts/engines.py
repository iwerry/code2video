#!/usr/bin/env python3
"""Motores de produção: detecção de disponibilidade REAL e seleção por objetivo e viabilidade.

CLI:
  python engines.py detect [--json]
  python engines.py select --project-type vertical-short [--need deterministic-seek,audio] [--prefer id] [--json]

detect   roda as sondas declaradas em engines/*/engine.json (binário no PATH, módulo Python importável,
         pacote Node resolvível, Chromium do Playwright) e diz o que está disponível AGORA.
         'disponível' não significa 'testado': o estado de verificação vem do manifesto.
select   filtra motores pelo tipo de projeto e capacidades, separa disponíveis de indisponíveis e de externos
         (que só geram plano). Devolve o bloco `engine` do contrato production-plan.
Códigos de saída: 0 motor disponível escolhido · 3 há candidatos mas nenhum disponível/executável aqui
(só plano) · 2 nenhum motor atende ao pedido.
"""
import argparse
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_engines(root=ROOT):
    out = {}
    for p in sorted(glob.glob(os.path.join(root, "engines", "*", "engine.json"))):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        out[d["id"]] = d
    return out


def _playwright_chromium():
    if os.environ.get("CHROMIUM_PATH") and os.path.isfile(os.environ["CHROMIUM_PATH"]):
        return True
    for base in (os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), "/opt/pw-browsers",
                 os.path.expanduser("~/.cache/ms-playwright")):
        if base and os.path.isdir(base):
            for name in os.listdir(base):
                if name.startswith(("chromium", "chrome")):
                    return True
    return False


def probe(p, cwd=None):
    kind, name = p["kind"], p["name"]
    if kind == "binary":
        return shutil.which(name) is not None
    if kind == "python_module":
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            return False
    if kind == "node_package":
        if not shutil.which("node"):
            return False
        r = subprocess.run(["node", "-e", f"require.resolve('{name}')"], capture_output=True, cwd=cwd)
        return r.returncode == 0
    if kind == "file":
        return os.path.exists(name)
    if kind == "playwright_chromium":
        return _playwright_chromium()
    return False


def availability(engine, cwd=None):
    if engine.get("external"):
        return {"available": False, "external": True, "missing": [], "note": "roda fora do agente; só gera plano/instruções"}
    probes = engine["availability"]["probes"]
    results = [(p, probe(p, cwd)) for p in probes]
    missing = [f"{p['kind']}:{p['name']}" for p, ok in results if not ok]
    return {"available": bool(probes) and not missing, "external": False, "missing": missing}


def select(engines, project_type, need=(), prefer=None, cwd=None):
    cands = []
    for e in engines.values():
        if project_type not in e["project_types"]:
            continue
        if not set(need) <= set(e["capabilities"]):
            continue
        cands.append((e, availability(e, cwd)))
    if not cands:
        return None, {"matched": []}
    runnable = [(e, a) for e, a in cands if a["available"]]
    order = sorted(runnable, key=lambda ea: (ea[0]["verification"]["state"] != "verified", ea[0]["id"]))
    if prefer:
        order.sort(key=lambda ea: ea[0]["id"] != prefer)
    info = {"matched": [e["id"] for e, _ in cands],
            "unavailable": {e["id"]: a["missing"] or ["externo"] for e, a in cands if not a["available"]}}
    if order:
        best = order[0][0]
        rest = [e["id"] for e, _ in order[1:]]
        why = (f"atende '{project_type}' e as capacidades {sorted(need) or '[]'}; disponível aqui; "
               f"verificação: {best['verification']['state']}")
        res = {"id": best["id"], "reason": why}
        if rest:
            res["fallback"] = rest[0]
        return res, info
    return None, info


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect"); d.add_argument("--json", action="store_true")
    s = sub.add_parser("select")
    s.add_argument("--project-type", required=True)
    s.add_argument("--need", default="")
    s.add_argument("--prefer")
    s.add_argument("--json", action="store_true")
    for p in (d, s):
        p.add_argument("--skill-dir", default=ROOT)
        p.add_argument("--cwd", help="pasta do projeto para resolver pacotes Node")
    a = ap.parse_args(argv)
    engines = load_engines(os.path.abspath(a.skill_dir))

    if a.cmd == "detect":
        rows = {eid: {**availability(e, a.cwd), "verification": e["verification"]["state"]} for eid, e in engines.items()}
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for eid, r in rows.items():
                status = "externo" if r["external"] else ("disponível" if r["available"] else "INDISPONÍVEL")
                miss = f"  falta: {', '.join(r['missing'])}" if r["missing"] else ""
                print(f"{eid:26s} {status:13s} [{r['verification']}]{miss}")
        return 0

    need = [x for x in a.need.split(",") if x]
    res, info = select(engines, a.project_type, need, a.prefer, a.cwd)
    if res:
        print(json.dumps({"engine": res, **info}, ensure_ascii=False, indent=2) if a.json
              else f"motor: {res['id']}\nmotivo: {res['reason']}" + (f"\nfallback: {res['fallback']}" if res.get("fallback") else ""))
        return 0
    if info["matched"]:
        print(f"nenhum motor executável aqui para '{a.project_type}'. Candidatos: {', '.join(info['matched'])}.", file=sys.stderr)
        for k, v in info["unavailable"].items():
            print(f"  - {k}: falta {', '.join(v)}", file=sys.stderr)
        print("Entregue apenas PLANO (status 'planned'), sem afirmar renderização.", file=sys.stderr)
        return 3
    print(f"nenhum motor declara suporte a '{a.project_type}'" + (f" com {need}" if need else "") +
          ". Tipos conhecidos: " + ", ".join(sorted({t for e in engines.values() for t in e['project_types']})), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
