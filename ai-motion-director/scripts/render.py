#!/usr/bin/env python3
"""Render determinístico: HTML com window.__seek(t) -> frames PNG -> MP4 (ffmpeg).

Uso:
  python render.py projeto/index.html saida.mp4 [--fps 30] [--audio trilha.wav] [--loudnorm]
                   [--report out/render-report.json]   # registro rastreável (contrato execution-report)
                   [--blur 4] [--shutter 0.5] [--start 0] [--end N] [--keep-frames]
                   [--crf 16] [--still 2.5]    # --still exporta um único frame em PNG

Contrato com a página (veja assets/template/index.html):
  window.__meta = { width, height, duration }   # segundos
  window.__ready = true                         # obrigatório: só depois de fontes/imagens carregarem
  window.__canvas = <canvas>                    # opcional: ativa captura rápida e sem perda
  window.__seek(t)                               # desenha o estado exato no instante t (síncrono)

Por que frame a frame: a página nunca roda em tempo real, então o resultado é idêntico
em qualquer máquina e animações pesadas não derrubam o fps.
Áudio: --audio arquivo.wav, OU defina window.__sfx = [{t,type,dur?,gain?}] na página e o render
sintetiza o som sozinho (mesma lista dos tempos visuais = sincronia sem copiar números).
--loudnorm normaliza para ~-14 LUFS (padrão de redes sociais).
fps: se --fps for omitido, usa window.__meta.fps (ou 30).
Render longo? Rode em segundo plano (nohup ... &) e acompanhe o log: 1080p ≈ 0,5 s/frame.
--blur N: motion blur real por acúmulo de N sub-frames dentro do obturador (--shutter, em
fração do frame; 0.5 = 180°). Custa N vezes mais tempo de render.
"""
import argparse, datetime, io, json, os, shutil, subprocess, sys, tempfile, time
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright


def chromium_path():
    for p in ("/opt/pw-browsers/chromium", os.environ.get("CHROMIUM_PATH", "")):
        if p and os.path.isfile(p):
            return p
    return None  # deixa o Playwright achar o seu


def grab(page, clip_w, clip_h, mode="canvas"):
    """canvas: lê o pixel buffer de window.__canvas (rápido, sem perda, ~85 ms/frame 1080p).
    screenshot: captura a página inteira (DOM/SVG/GSAP/WebGL); PNG é lento (~700 ms), JPEG ~50 ms."""
    if mode == "canvas":
        import base64
        d = page.evaluate("window.__canvas.toDataURL('image/png')")
        return Image.open(io.BytesIO(base64.b64decode(d.split(",", 1)[1]))).convert("RGB")
    kind = "jpeg" if mode == "jpeg" else "png"
    kw = {"quality": 97} if kind == "jpeg" else {}
    png = page.screenshot(type=kind, clip={"x": 0, "y": 0, "width": clip_w, "height": clip_h}, **kw)
    return Image.open(io.BytesIO(png)).convert("RGB")


STATS = {}  # preenchido durante a execução; alimenta o --report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="grava o resultado da execução (JSON, contrato execution-report)")
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("--fps", type=int, default=None, help="padrão: window.__meta.fps ou 30")
    ap.add_argument("--audio")
    ap.add_argument("--loudnorm", action="store_true", help="normaliza áudio para ~-14 LUFS")
    ap.add_argument("--blur", type=int, default=1, help="sub-frames por frame (1 = sem blur)")
    ap.add_argument("--shutter", type=float, default=0.5)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--still", type=float, help="exporta só o frame em t (s) como PNG em OUT")
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--capture", choices=["auto", "canvas", "png", "jpeg"], default="auto",
                    help="auto: canvas se a página expõe window.__canvas, senão screenshot jpeg")
    a = ap.parse_args()

    url = "file://" + os.path.abspath(a.html)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path(),
                                    args=["--force-device-scale-factor=1", "--hide-scrollbars"])
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        logs = []
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: logs.append(f"[pageerror] {e}"))
        page.goto(url)
        try:
            page.wait_for_function("window.__ready === true", timeout=30000)
        except Exception:
            msg = "A página não definiu window.__ready = true em 30 s (defina-o depois de fontes/imagens carregarem)."
            sys.exit(msg + (" Avisos da página: " + "; ".join(logs) if logs else ""))
        meta = page.evaluate("window.__meta")
        if not meta or "__seek" not in page.evaluate("Object.keys(window)"):
            sys.exit("A página precisa definir window.__meta e window.__seek(t). Veja assets/template/index.html")
        mode = a.capture
        if mode == "auto":
            mode = "canvas" if page.evaluate("!!window.__canvas") else "jpeg"
        print("captura:", mode)
        W, H, dur = int(meta["width"]), int(meta["height"]), float(meta["duration"])
        if a.fps is None:
            a.fps = int(meta.get("fps", 30))
        STATS.update(width=W, height=H, fps=a.fps, capture=mode, audio="file" if a.audio else "none", logs=logs)
        sfx_events = page.evaluate("window.__sfx || null")
        page.set_viewport_size({"width": W, "height": H})
        page.evaluate("document.fonts && document.fonts.ready")

        if a.still is not None:
            page.evaluate(f"window.__seek({a.still})")
            grab(page, W, H, mode).save(a.out)
            STATS.update(frames=1)
            print(f"still salvo: {a.out}")
            browser.close()
            return

        end = min(a.end if a.end else dur, dur)
        n = int(round((end - a.start) * a.fps))
        tmp = tempfile.mkdtemp(prefix="frames_")
        for i in range(n):
            t0 = a.start + i / a.fps
            if a.blur > 1:
                acc = np.zeros((H, W, 3), dtype=np.float32)
                for s in range(a.blur):
                    ts = t0 + (s / a.blur - 0.5) * a.shutter / a.fps + 0.0
                    page.evaluate(f"window.__seek({max(ts, 0)})")
                    acc += np.asarray(grab(page, W, H, mode), dtype=np.float32)
                img = Image.fromarray((acc / a.blur).round().astype(np.uint8))
            else:
                page.evaluate(f"window.__seek({t0})")
                img = grab(page, W, H, mode)
            img.save(os.path.join(tmp, f"f{i:06d}.png"), compress_level=1)
            if i % (a.fps * 2) == 0:
                print(f"{i}/{n} frames", flush=True)
        print(f"\n{n}/{n} frames")
        STATS.update(frames=n)
        browser.close()

    if logs:
        print("Avisos/erros da página:\n  " + "\n  ".join(sorted(set(logs))))

    audio = a.audio
    if not audio and sfx_events:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import synth_sfx
        audio = os.path.join(tmp, "sfx.wav")
        synth_sfx.write_wav(synth_sfx.render_events(sfx_events, dur), audio)
        print(f"áudio sintetizado a partir de window.__sfx ({len(sfx_events)} eventos)")
        STATS["audio"] = "synth-sfx"
        a.start = 0.0 if a.start is None else a.start
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
           "-i", os.path.join(tmp, "f%06d.png")]
    if audio:
        cmd += ["-ss", str(a.start), "-t", str(end - a.start), "-i", audio]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(a.crf), "-preset", "medium",
            "-movflags", "+faststart"]
    if audio:
        if a.loudnorm:
            cmd += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [a.out]
    subprocess.run(cmd, check=True)
    if a.keep_frames:
        print("frames em", tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    print("ok:", a.out)


def run():
    """Executa main() e, se pedido (--report), registra o resultado como fato: ok, tempos, saída, erros."""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--report")
    known, _ = pre.parse_known_args()
    started = datetime.datetime.now(datetime.timezone.utc)
    t0 = time.time()
    err, code = None, 0
    try:
        main()
    except SystemExit as e:
        code = e.code
        if e.code not in (None, 0):
            err = str(e.code)
    except Exception as e:  # noqa: BLE001 - queremos registrar qualquer falha
        err, code = f"{type(e).__name__}: {e}", 1
    if known.report:
        out = next((x for x in sys.argv[1:] if not x.startswith("-")), None)
        outs = [x for x in sys.argv[1:] if not x.startswith("-")][1:2]
        ok = err is None
        rep = {"tool": "render.py", "command": " ".join(["render.py"] + sys.argv[1:]),
               "started_at": started.isoformat(), "duration_s": round(time.time() - t0, 2), "ok": ok,
               "outputs": [o for o in outs if ok and os.path.exists(o)],
               "page_messages": sorted(set(STATS.get("logs", []))), "status": "executed"}
        for k in ("frames", "fps", "width", "height", "capture", "audio"):
            if k in STATS:
                rep[k] = STATS[k]
        if ok:
            rep["evidence"] = [{"type": "file", "ref": o} for o in rep["outputs"]] or [{"type": "log", "ref": "stdout do render.py"}]
        else:
            rep["errors"] = [err]
            rep["evidence"] = [{"type": "log", "ref": err[:300]}]
        os.makedirs(os.path.dirname(os.path.abspath(known.report)), exist_ok=True)
        with open(known.report, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print("relatório:", known.report)
    if err is not None:
        sys.exit(code if code not in (None, 0) else 1)


if __name__ == "__main__":
    run()
