#!/usr/bin/env python3
"""Verificação objetiva de um vídeo renderizado.

Uso: python inspect_video.py video.mp4 [--sheet folha.png] [--cols 6] [--count 15 | --times 0,1.5,3]
(--times substitui --count: use um OU outro. Para zoom num impacto: --times 3.1,3.2,3.3 --cols 3)

Imprime duração, resolução, fps, presença de áudio e uma checagem de quadros
(pretos/congelados). Gera uma contact sheet para você OLHAR os frames com Read:
timecodes de roteiro só provam algo depois de vistos.
"""
import argparse, json, os, signal, subprocess, tempfile
signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # sem BrokenPipeError ao usar | head
import numpy as np
from PIL import Image, ImageDraw


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                   "-of", "json", path])
    return json.loads(out)


def frame_at(path, t, w):
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", path,
                    "-frames:v", "1", "-vf", f"scale={w}:-1", f], check=True)
    im = Image.open(f).convert("RGB")
    os.unlink(f)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--sheet")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--thumb", type=int, default=384)
    ap.add_argument("--times", help="lista separada por vírgula, em segundos")
    ap.add_argument("--count", type=int, default=15)
    ap.add_argument("--report", help="grava a validação TÉCNICA (JSON, contrato qa-report, kind=technical)")
    a = ap.parse_args()

    info = probe(a.video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    dur = float(info["format"]["duration"])
    print(f"duração {dur:.2f}s | {v['width']}x{v['height']} | {v['r_frame_rate']} fps | "
          f"codec {v['codec_name']} | áudio: {'sim' if has_audio else 'não'}")

    if a.times:
        print("nota: --times foi usado; --count é ignorado")
    times = ([float(x) for x in a.times.split(",")] if a.times
             else list(np.linspace(0.05, max(dur - 0.1, 0.1), a.count)))
    frames, prev, flags = [], None, []
    for t in times:
        im = frame_at(a.video, t, a.thumb)
        arr = np.asarray(im, dtype=np.float32)
        if arr.mean() < 3:
            flags.append(f"t={t:.2f}s quase preto")
        if prev is not None and np.abs(arr - prev).mean() < 0.15:
            flags.append(f"t={t:.2f}s idêntico ao quadro anterior amostrado (parado?)")
        prev = arr
        frames.append((t, im))
    print("alertas:" if flags else "alertas: nenhum")
    for f in flags:
        print("  -", f)
    print("(parado nem sempre é erro: pausas dramáticas são intencionais — confira no roteiro)")

    if a.sheet:
        cols = a.cols
        rows = (len(frames) + cols - 1) // cols
        tw, th = frames[0][1].size
        sheet = Image.new("RGB", (cols * tw, rows * (th + 18)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, (t, im) in enumerate(frames):
            x, y = (i % cols) * tw, (i // cols) * (th + 18)
            sheet.paste(im, (x, y + 18))
            d.text((x + 4, y + 3), f"{t:.2f}s", fill=(255, 255, 255))
        sheet.save(a.sheet)
        print("contact sheet:", a.sheet)

    if a.report:
        # Validação técnica = medições + alertas objetivos. Não julga estética e NUNCA marca 'validated':
        # a avaliação criativa (olhar a folha de contato) é registrada à parte, em qa-creative.json.
        findings = []
        for f in flags:
            black = "preto" in f
            findings.append({
                "problem": f, "evidence": f"quadro amostrado em {f.split()[0]}",
                "impact": "tela vazia não intencional" if black else "possível trecho morto (ou pausa dramática intencional)",
                "fix": "conferir no roteiro se é intencional; se não for, corrigir a cena nesse tempo",
                "priority": "media" if black else "baixa"})
        rep = {"kind": "technical", "target": os.path.abspath(a.video),
               "measurements": {"duration_s": round(dur, 3), "width": v["width"], "height": v["height"],
                                "fps": v["r_frame_rate"], "codec": v["codec_name"], "has_audio": has_audio,
                                "sampled_frames": len(times)},
               "findings": findings, "status": "executed",
               "evidence": [{"type": "file", "ref": os.path.abspath(a.sheet)}] if a.sheet
                           else [{"type": "metric", "ref": f"ffprobe + {len(times)} quadros amostrados"}]}
        os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=2)
        print("relatório técnico:", a.report)


if __name__ == "__main__":
    main()
