#!/usr/bin/env python3
"""Automação de produção: prepara, valida, renderiza, inspeciona e reúne um projeto de vídeo, com registro rastreável.

Layout de um projeto (tudo opcional exceto index.html):
  projeto/
    project.json            perfil, estilo, título (criado por 'init')
    brief.json  script.json  plan.json  recommendations.json     artefatos dos módulos (contratos)
    index.html + motion-kit.js                                     o vídeo (motor canvas-motion-kit)
    out/render-report.json  out/qa-technical.json  out/folha.png   resultados REAIS de execução
    qa-creative.json                                                avaliação criativa (feita por quem olhou a folha)
    deliver/                                                        pacote final (criado por 'bundle')

Comandos:
  pipeline.py init <pasta> [--profile vertical-short] [--style tech-premium-dark] [--title T] [--duration S]
  pipeline.py check <pasta>                 valida artefatos contra contratos + coerência (META × perfil × roteiro)
  pipeline.py render <pasta> [--fps N] [--blur N] [--loudnorm] [--still T] [--capture ...]
  pipeline.py inspect <pasta>               validação TÉCNICA (medidas + folha de contato)
  pipeline.py bundle <pasta>                reúne finais + MANIFEST.json (recusa se não houve render bem-sucedido)
  pipeline.py status <pasta>                o que existe e em que estado

Princípio: este script só registra o que de fato executou. 'bundle' não afirma renderização que não
aconteceu, e 'inspect' nunca marca algo como 'validated' (olhar a folha é um passo humano/agente).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import contracts  # noqa: E402

PY = sys.executable
META_RE = re.compile(r"const META = \{[^}]*\};")


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def profile_of(proj):
    pj = os.path.join(proj, "project.json")
    if not os.path.isfile(pj):
        return None
    pid = load_json(pj).get("profile")
    pp = os.path.join(ROOT, "profiles", f"{pid}.json")
    return load_json(pp) if os.path.isfile(pp) else None


def read_meta(html_path):
    """Lê o objeto META do index.html (sem executar nada)."""
    m = META_RE.search(open(html_path, encoding="utf-8").read())
    if not m:
        return None
    out = {}
    for k in ("width", "height", "duration", "fps"):
        mm = re.search(rf"{k}\s*:\s*([0-9.]+)", m.group(0))
        if mm:
            out[k] = float(mm.group(1))
    return out


def cmd_init(a):
    proj = os.path.abspath(a.dir)
    if os.path.exists(os.path.join(proj, "index.html")) and not a.force:
        print(f"erro: {proj}/index.html já existe (use --force para sobrescrever)", file=sys.stderr)
        return 1
    pp = os.path.join(ROOT, "profiles", f"{a.profile}.json")
    if not os.path.isfile(pp):
        have = ", ".join(sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, "profiles"))))
        print(f"erro: perfil '{a.profile}' não existe. Disponíveis: {have}", file=sys.stderr)
        return 2
    if a.style and not os.path.isfile(os.path.join(ROOT, "styles", f"{a.style}.json")):
        print(f"erro: estilo '{a.style}' não existe", file=sys.stderr)
        return 2
    prof = load_json(pp)
    os.makedirs(proj, exist_ok=True)
    for f in ("index.html", "motion-kit.js"):
        shutil.copy(os.path.join(ROOT, "assets", "template", f), os.path.join(proj, f))
    dur = a.duration or round(sum(prof["duration_range_s"]) / 2 / 0.5) * 0.5
    html = open(os.path.join(proj, "index.html"), encoding="utf-8").read()
    html = META_RE.sub(f"const META = {{ width: {prof['width']}, height: {prof['height']}, duration: {dur}, fps: {prof['fps']} }};", html)
    open(os.path.join(proj, "index.html"), "w", encoding="utf-8").write(html)
    json.dump({"title": a.title or os.path.basename(proj), "profile": a.profile, "style": a.style,
               "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()},
              open(os.path.join(proj, "project.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.makedirs(os.path.join(proj, "out"), exist_ok=True)
    print(f"projeto criado em {proj} (perfil {a.profile}: {prof['width']}x{prof['height']} @ {prof['fps']} fps, {dur}s)")
    print("o template traz uma demo; troque as cenas pelo roteiro. Próximo: pipeline.py render", a.dir, "--still 3")
    return 0


def cmd_check(a):
    proj = os.path.abspath(a.dir)
    problems = 0
    r = contracts.main(["check-dir", proj])
    problems += bool(r)
    html = os.path.join(proj, "index.html")
    if os.path.isfile(html):
        text = open(html, encoding="utf-8").read()
        for token, why in (("__meta", "window.__meta"), ("__seek", "window.__seek(t)"), ("__ready", "window.__ready = true")):
            if token not in text:
                print(f"FAIL index.html: falta {why} (contrato com o render)")
                problems += 1
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)       # ignora comentários
        code = re.sub(r"(?m)^\s*//.*$|\s//[^\n]*$", "", code)
        for bad in ("Math.random", "Date.now"):
            if bad in code:
                print(f"AVISO index.html usa {bad}: animação não determinística (render frame a frame pode divergir)")
        meta = read_meta(html)
        prof = profile_of(proj)
        if meta and prof:
            for k_meta, k_prof in (("width", "width"), ("height", "height"), ("fps", "fps")):
                if k_meta in meta and int(meta[k_meta]) != prof[k_prof]:
                    print(f"AVISO META.{k_meta}={int(meta[k_meta])} difere do perfil '{prof['id']}' ({prof[k_prof]})")
            lo, hi = prof["duration_range_s"]
            if "duration" in meta and not (lo <= meta["duration"] <= hi):
                print(f"AVISO duração {meta['duration']}s fora da faixa típica do perfil ({lo}-{hi}s)")
        sp = os.path.join(proj, "script.json")
        if meta and os.path.isfile(sp):
            sd = load_json(sp).get("duration_s")
            if sd is not None and "duration" in meta and abs(sd - meta["duration"]) > 0.05:
                print(f"FAIL script.json duration_s={sd}s ≠ META.duration={meta['duration']}s (roteiro e vídeo divergem)")
                problems += 1
    else:
        print("AVISO sem index.html (ainda não é um projeto renderizável)")
    print("RESULTADO:", "problemas encontrados" if problems else "ok")
    return 1 if problems else 0


def cmd_render(a):
    proj = os.path.abspath(a.dir)
    html = os.path.join(proj, "index.html")
    if not os.path.isfile(html):
        print(f"erro: {html} não existe (rode 'init' ou crie o projeto)", file=sys.stderr)
        return 1
    out_dir = os.path.join(proj, "out")
    os.makedirs(out_dir, exist_ok=True)
    report = os.path.join(out_dir, "render-report.json")
    if a.still is not None:
        out = os.path.join(out_dir, f"still-{a.still}.png")
        cmd = [PY, os.path.join(HERE, "render.py"), html, out, "--still", str(a.still)]
        report = os.path.join(out_dir, "still-report.json")
    else:
        out = os.path.join(out_dir, "video.mp4")
        cmd = [PY, os.path.join(HERE, "render.py"), html, out]
        if a.fps: cmd += ["--fps", str(a.fps)]
        if a.blur and a.blur > 1: cmd += ["--blur", str(a.blur)]
        if a.loudnorm: cmd.append("--loudnorm")
        if a.audio: cmd += ["--audio", a.audio]
        if a.start is not None: cmd += ["--start", str(a.start)]
        if a.end is not None: cmd += ["--end", str(a.end)]
    if a.capture: cmd += ["--capture", a.capture]
    cmd += ["--report", report]
    rc = subprocess.run(cmd).returncode
    errs = contracts.validate_file("execution-report", report) if os.path.isfile(report) else ["relatório não foi gerado"]
    if errs:
        print("AVISO: relatório de execução inválido:", *errs, sep="\n  - ")
    rep = load_json(report) if os.path.isfile(report) else {"ok": False}
    print(f"RENDER {'OK' if rc == 0 and rep.get('ok') else 'FALHOU'} → {out if rc == 0 else report}")
    return 0 if rc == 0 and rep.get("ok") else 1


def cmd_inspect(a):
    proj = os.path.abspath(a.dir)
    video = os.path.join(proj, "out", "video.mp4")
    if not os.path.isfile(video):
        print(f"erro: {video} não existe; renderize antes (pipeline.py render)", file=sys.stderr)
        return 1
    sheet = os.path.join(proj, "out", "folha.png")
    rc = subprocess.run([PY, os.path.join(HERE, "inspect_video.py"), video, "--sheet", sheet,
                         "--report", os.path.join(proj, "out", "qa-technical.json"), "--count", str(a.count)]).returncode
    errs = contracts.validate_file("qa-report", os.path.join(proj, "out", "qa-technical.json"))
    if errs:
        print("AVISO: relatório técnico inválido:", *errs, sep="\n  - ")
    print("\nPRÓXIMO PASSO (não automatizável): abra", sheet, "e registre a avaliação CRIATIVA em qa-creative.json "
          "(contrato qa-report, kind=creative). A inspeção técnica não julga estética.")
    return rc


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_bundle(a):
    proj = os.path.abspath(a.dir)
    rr = os.path.join(proj, "out", "render-report.json")
    video = os.path.join(proj, "out", "video.mp4")
    if not (os.path.isfile(rr) and load_json(rr).get("ok") and os.path.isfile(video)):
        print("erro: não há render bem-sucedido registrado (out/render-report.json com ok=true + out/video.mp4). "
              "Não vou empacotar algo que não foi renderizado.", file=sys.stderr)
        return 1
    dest = os.path.join(proj, "deliver")
    os.makedirs(dest, exist_ok=True)
    items = [("video.mp4", video)]
    for name, src in (("folha.png", "out/folha.png"), ("render-report.json", "out/render-report.json"),
                      ("qa-technical.json", "out/qa-technical.json"), ("qa-creative.json", "qa-creative.json"),
                      ("brief.json", "brief.json"), ("script.json", "script.json"), ("plan.json", "plan.json")):
        sp = os.path.join(proj, src)
        if os.path.isfile(sp):
            items.append((name, sp))
    for f in ("index.html", "motion-kit.js"):
        items.append((f"source/{f}", os.path.join(proj, f)))
    manifest = {"created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "files": []}
    for name, sp in items:
        dp = os.path.join(dest, name)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.copy(sp, dp)
        manifest["files"].append({"name": name, "bytes": os.path.getsize(dp), "sha256": sha256(dp)})
    manifest["creative_review"] = "presente" if os.path.isfile(os.path.join(proj, "qa-creative.json")) else "AUSENTE (nenhuma avaliação criativa registrada)"
    json.dump(manifest, open(os.path.join(dest, "MANIFEST.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"pacote em {dest} ({len(items)} arquivos). Avaliação criativa: {manifest['creative_review']}")
    return 0


def cmd_status(a):
    proj = os.path.abspath(a.dir)
    rows = [("index.html", None), ("project.json", None)] + [(f, c) for f, c in contracts.PROJECT_FILES.items()]
    paths = {"render-report.json": "out/render-report.json", "qa-technical.json": "out/qa-technical.json"}
    for f, c in rows:
        p = os.path.join(proj, paths.get(f, f))
        if not os.path.isfile(p):
            print(f"  --       {f}")
            continue
        st = "existe"
        if f.endswith(".json") and c:
            d = load_json(p)
            st = d.get("status", "?") + (" (sem evidência!)" if d.get("status") in ("executed", "validated") and not d.get("evidence") else "")
        print(f"  {st:9s}  {f}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("dir"); i.add_argument("--profile", default="landscape-brand")
    i.add_argument("--style"); i.add_argument("--title"); i.add_argument("--duration", type=float); i.add_argument("--force", action="store_true")
    for n in ("check", "inspect", "bundle", "status"):
        sub.add_parser(n).add_argument("dir")
    sub.choices["inspect"].add_argument("--count", type=int, default=15)
    r = sub.add_parser("render"); r.add_argument("dir")
    r.add_argument("--fps", type=int); r.add_argument("--blur", type=int); r.add_argument("--loudnorm", action="store_true")
    r.add_argument("--still", type=float); r.add_argument("--audio"); r.add_argument("--start", type=float)
    r.add_argument("--end", type=float); r.add_argument("--capture", choices=["auto", "canvas", "png", "jpeg"])
    a = ap.parse_args(argv)
    return {"init": cmd_init, "check": cmd_check, "render": cmd_render, "inspect": cmd_inspect,
            "bundle": cmd_bundle, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
