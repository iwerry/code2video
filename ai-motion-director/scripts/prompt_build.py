#!/usr/bin/env python3
"""Monta o prompt final de geração a partir de uma especificação de plano (shot-spec) e de um perfil de ferramenta.

  python prompt_build.py --shot plano.json --profile generic-video [--json]
  python prompt_build.py --list

Separação de responsabilidades: o shot-spec carrega a DECISÃO CRIATIVA (independente de ferramenta);
o prompt-profile carrega o que é particular da ferramenta (template, limites, limitações). Trocar de
ferramenta = trocar o perfil; o roteiro e o shot-spec não mudam.

Avisos (não bloqueiam, mas aparecem na saída): perfil não verificado, prompt acima do limite de
palavras, texto na imagem em ferramenta sem suporte confirmado, instruções de câmera incompatíveis
(estática + movimento intenso), ausência de referência de continuidade.
Erros (bloqueiam): shot-spec ou perfil inválidos pelo contrato; perfil desconhecido.
Nada aqui chama ferramentas externas: o resultado é texto com status 'generated' (não 'executed').
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import contracts  # noqa: E402

ROOT = os.path.dirname(HERE)
STATIC = re.compile(r"\b(est[aá]tic[ao]|fixa|fixo|locked|static|tripé)\b", re.I)
MOVING = re.compile(r"\b(push|pull|pan|tilt|orbit|dolly|zoom|travelling|handheld|em movimento|tracking)\b", re.I)


def load_profiles(root=ROOT):
    out = {}
    for p in sorted(glob.glob(os.path.join(root, "prompt-profiles", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        out[d["id"]] = d
    return out


def build(shot, profile):
    """Retorna (prompt, avisos). Segmentos do template com campo vazio são descartados."""
    warns = []
    values = {k: (", ".join(v) if isinstance(v, list) else str(v)) for k, v in shot.items() if v not in (None, "", [])}
    segs = []
    for seg in profile["template"].split("|"):
        seg = seg.strip()
        names = re.findall(r"\{(\w+)\}", seg)
        if names and any(n in values for n in names):   # mantém o segmento se ao menos um campo existe
            txt = re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), ""), seg)
            txt = re.sub(r"\s*,\s*(?=,|$)", "", txt)       # vírgulas órfãs de campos vazios
            txt = re.sub(r"(:)\s*,\s*", r"\1 ", txt).strip(" ,")
            segs.append(txt)
    prompt = ". ".join(segs)

    if not profile["capabilities_verified"]:
        warns.append(f"perfil '{profile['id']}' tem capacidades NÃO verificadas: confirme na documentação da ferramenta antes de depender delas")
    words = len(prompt.split())
    if profile.get("max_prompt_words") and words > profile["max_prompt_words"]:
        warns.append(f"prompt com {words} palavras excede o limite do perfil ({profile['max_prompt_words']}): corte detalhes redundantes")
    cam = shot.get("camera_motion", "")
    if cam and STATIC.search(cam) and MOVING.search(cam):
        warns.append("camera_motion mistura câmera estática e movimento: descreva a sequência (ex.: 'fixa por 2 s, depois push-in lento')")
    if re.search(r"[\"“”']", shot.get("subject", "") + shot.get("action", "") + shot.get("style", "")) \
            and profile.get("supports_text_in_image") is not True:
        warns.append("há texto entre aspas no plano e a ferramenta não tem suporte a texto confirmado: componha o texto por código (Canvas)")
    if not shot.get("continuity_refs"):
        warns.append("sem continuity_refs: se este plano precisa combinar com outros, defina referências (personagem, figurino, paleta, lente)")
    for lim in profile["known_limitations"][:2]:
        warns.append(f"limitação conhecida: {lim}")
    return prompt, warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shot")
    ap.add_argument("--profile")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skill-dir", default=ROOT)
    a = ap.parse_args(argv)
    root = os.path.abspath(a.skill_dir)
    profiles = load_profiles(root)

    if a.list:
        for pid, p in profiles.items():
            print(f"{pid:20s} {p['medium']:16s} verificado={p['capabilities_verified']}")
        return 0
    if not (a.shot and a.profile):
        ap.error("informe --shot e --profile (ou --list)")
    if a.profile not in profiles:
        print(f"erro: perfil desconhecido '{a.profile}'. Disponíveis: {', '.join(profiles)}", file=sys.stderr)
        return 2
    errs = contracts.validate_file("shot-spec", a.shot)
    errs += [f"perfil: {e}" for e in contracts.validate("prompt-profile", profiles[a.profile])]
    if errs:
        print("entrada inválida:", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        return 1
    shot = json.load(open(a.shot, encoding="utf-8"))
    prompt, warns = build(shot, profiles[a.profile])
    if a.json:
        print(json.dumps({"id": shot["id"], "profile": a.profile, "prompt": prompt, "warnings": warns,
                          "status": "generated"}, ensure_ascii=False, indent=2))
    else:
        print(prompt)
        print("\n[status: generated — prompt montado, NÃO enviado a nenhuma ferramenta]")
        for w_ in warns:
            print("  aviso:", w_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
