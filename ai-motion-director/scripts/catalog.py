#!/usr/bin/env python3
"""Catálogo pesquisável de técnicas de motion graphics (dados em catalog/techniques/**/*.json).

Adicionar técnica = soltar um .json (array de técnicas) em catalog/techniques/. Nenhum código nem o
Core precisam mudar; `catalog.py check` valida o arquivo novo contra o contrato 'technique'.

CLI:
  python catalog.py search [--intent hook] [--emotion tension] [--category typography]
                           [--motion-type path] [--context short-social] [--max-complexity 3]
                           [--feasible A|AB|ABC] [--engine canvas-motion-kit] [--text palavra] [--limit 8]
  python catalog.py show <id>
  python catalog.py facets            # valores existentes em cada faceta
  python catalog.py check             # valida todos os arquivos (ids únicos, contrato, motores)

Ranking: cada filtro de faceta (intent/emotion/...) é obrigatório; quando há vários valores na mesma
faceta (--intent a,b) basta casar um. Empate: menor complexidade e maior viabilidade (A>B>C) primeiro.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import contracts  # noqa: E402

ROOT = os.path.dirname(HERE)
FEAS_RANK = {"A": 0, "B": 1, "C": 2}


def files(root=ROOT):
    return sorted(glob.glob(os.path.join(root, "catalog", "techniques", "**", "*.json"), recursive=True))


def load_all(root=ROOT):
    out = []
    for p in files(root):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        out.extend(data if isinstance(data, list) else [data])
    return out


def check(root=ROOT):
    errs, seen = [], {}
    for p in files(root):
        rel = os.path.relpath(p, root)
        try:
            data = json.load(open(p, encoding="utf-8"))
        except json.JSONDecodeError as e:
            errs.append(f"{rel}: JSON inválido (linha {e.lineno}): {e.msg}")
            continue
        if not isinstance(data, list):
            errs.append(f"{rel}: o arquivo deve conter um array de técnicas")
            continue
        for i, t in enumerate(data):
            for e in contracts.validate("technique", t):
                errs.append(f"{rel}[{i}] ({t.get('id', '?')}): {e}")
            tid = t.get("id")
            if tid in seen:
                errs.append(f"{rel}[{i}]: id duplicado '{tid}' (já em {seen[tid]})")
            seen[tid] = rel
    return errs


def _csv(v):
    return [x.strip() for x in v.split(",") if x.strip()] if v else None


def search(techs, intent=None, emotion=None, category=None, motion_type=None, context=None,
           max_complexity=None, feasible=None, engine=None, text=None):
    def any_of(have, want):
        return want is None or any(w in have for w in want)

    res = []
    for t in techs:
        if not any_of(t["narrative_intents"], intent): continue
        if not any_of(t["emotions"], emotion): continue
        if not any_of([t["category"]], category): continue
        if not any_of([t["motion_type"]], motion_type): continue
        if context and not (set(context) & set(t["contexts"]) or "any" in t["contexts"]): continue
        if max_complexity is not None and t["complexity"] > max_complexity: continue
        if feasible and t["feasibility"] not in feasible: continue
        if engine and not any(e in t["engines"] for e in engine): continue
        if text:
            blob = " ".join([t["name"], " ".join(t.get("aliases", [])), t["when_to_use"], t["why"]]).lower()
            if text.lower() not in blob: continue
        res.append(t)
    res.sort(key=lambda t: (t["complexity"], FEAS_RANK[t["feasibility"]], t["id"]))
    return res


def facets(techs):
    out = {}
    for key in ("narrative_intents", "emotions", "contexts", "engines"):
        out[key] = sorted({v for t in techs for v in t[key]})
    for key in ("category", "motion_type", "feasibility"):
        out[key] = sorted({t[key] for t in techs})
    return out


def fmt_row(t):
    return (f"{t['id']:34s} {t['feasibility']} c{t['complexity']}  {t['category']:20s} "
            f"intents={','.join(t['narrative_intents'])}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    for k in ("intent", "emotion", "category", "motion-type", "context", "engine"):
        s.add_argument(f"--{k}")
    s.add_argument("--max-complexity", type=int)
    s.add_argument("--feasible", help="letras aceitas, ex.: A ou AB")
    s.add_argument("--text")
    s.add_argument("--limit", type=int, default=12)
    s.add_argument("--json", action="store_true")
    sh = sub.add_parser("show"); sh.add_argument("id")
    sub.add_parser("facets"); sub.add_parser("check")
    for p in (s, sh, sub.choices["facets"], sub.choices["check"]):
        p.add_argument("--skill-dir", default=ROOT)
    a = ap.parse_args(argv)
    root = os.path.abspath(a.skill_dir)

    if a.cmd == "check":
        errs = check(root)
        if errs:
            print(f"CATÁLOGO INVÁLIDO: {len(errs)} problema(s)")
            for e in errs: print("  -", e)
            return 1
        print(f"ok: {len(load_all(root))} técnicas em {len(files(root))} arquivo(s)")
        return 0
    techs = load_all(root)
    if a.cmd == "facets":
        for k, v in facets(techs).items():
            print(f"{k}: {', '.join(map(str, v))}")
        return 0
    if a.cmd == "show":
        hit = next((t for t in techs if t["id"] == a.id), None)
        if not hit:
            near = [t["id"] for t in techs if a.id in t["id"]][:5]
            print(f"técnica desconhecida: {a.id}" + (f" (parecidas: {', '.join(near)})" if near else ""), file=sys.stderr)
            return 2
        print(json.dumps(hit, ensure_ascii=False, indent=2))
        return 0
    res = search(techs, _csv(a.intent), _csv(a.emotion), _csv(a.category), _csv(a.motion_type), _csv(a.context),
                 a.max_complexity, a.feasible, _csv(a.engine), a.text)
    if a.json:
        print(json.dumps(res[: a.limit], ensure_ascii=False, indent=2))
    else:
        print(f"{len(res)} técnica(s)" + (f", mostrando {a.limit}" if len(res) > a.limit else ""))
        for t in res[: a.limit]:
            print(" ", fmt_row(t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
