#!/usr/bin/env python3
"""Extrai dados REAIS de uma faixa de áudio para sincronizar o motion (nada de BPM inventado).

Uso: python audio_map.py faixa.mp3 --out audio.json [--fps 30]

Saída (JSON): duration, fps, rms[] (energia por frame, 0-1), onsets[] (tempos em s de
transientes), bpm_estimate (heurística por autocorrelação dos onsets; trate como estimativa).
No HTML, embuta o JSON e use rms[Math.floor(t*fps)] para reatividade.
Requer ffmpeg e numpy.
"""
import argparse, json, subprocess
import numpy as np

SR = 22050


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", default="audio.json")
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()

    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", a.audio, "-ac", "1", "-ar", str(SR),
                                   "-f", "f32le", "-"])
    x = np.frombuffer(raw, dtype=np.float32)
    dur = len(x) / SR
    hop = SR // a.fps
    n = len(x) // hop
    frames = x[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    rms = rms / (rms.max() + 1e-9)

    # onsets: aumento positivo de energia (spectral-flux simplificado no domínio do RMS curto)
    h2 = SR // 100
    m = len(x) // h2
    e = np.sqrt((x[: m * h2].reshape(m, h2) ** 2).mean(axis=1))
    flux = np.maximum(np.diff(e, prepend=e[0]), 0)
    thr = flux.mean() + 1.5 * flux.std()
    onsets, last = [], -1
    for i, f in enumerate(flux):
        t = i / 100
        if f > thr and t - last > 0.1:
            onsets.append(round(t, 3))
            last = t

    bpm = None
    if len(flux) > 400:
        ac = np.correlate(flux - flux.mean(), flux - flux.mean(), mode="full")[len(flux) - 1:]
        lo, hi = int(100 * 60 / 200), int(100 * 60 / 60)  # 60-200 BPM
        lag = lo + int(np.argmax(ac[lo:hi]))
        bpm = round(6000 / lag, 1)

    json.dump({"duration": round(dur, 3), "fps": a.fps, "rms": [round(float(v), 4) for v in rms],
               "onsets": onsets, "bpm_estimate": bpm}, open(a.out, "w"))
    print(f"{dur:.1f}s | {len(onsets)} onsets | bpm≈{bpm} (estimativa) -> {a.out}")


if __name__ == "__main__":
    main()
