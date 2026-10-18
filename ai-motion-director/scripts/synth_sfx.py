#!/usr/bin/env python3
"""Sintetiza sound design simples (numpy puro) e monta uma trilha a partir de uma lista de eventos.

Atalho: se a página definir window.__sfx = [...], o render.py sintetiza sozinho (não precisa deste CLI).
Uso:
  python synth_sfx.py --events eventos.json --duration 9 --out sfx.wav
  eventos.json: [{"t": 3.2, "type": "impact"}, {"t": 0.0, "type": "riser", "dur": 3.2}, ...]
  tipos: impact, riser, whoosh, tick, pop, drone, shimmer
  campos opcionais: "gain" (0-1, padrão 0.8), "dur" (s), "freq" (Hz)

Serve para dar vida ao protótipo e travar a sincronia imagem-som no tempo certo.
Não substitui sound design profissional: é um bom rascunho, não o master. Diga isso ao usuário.
"""
import argparse, json, wave
import numpy as np

SR = 44100


def noise(n, seed=1):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = (1 - a) * x[i] + a * y[i - 1]
    return y


def impact(dur=1.4, freq=48, **_):
    n = int(SR * dur); t = np.arange(n) / SR
    sweep = freq * (1 + 3 * np.exp(-t * 18))                 # queda de pitch: soco no peito
    body = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t * 3.2)
    click = lowpass(noise(n, 3), 6000) * np.exp(-t * 60) * 0.7
    tail = lowpass(noise(n, 4), 900) * np.exp(-t * 2.2) * 0.35
    return body + click + tail


def riser(dur=3.0, **_):
    n = int(SR * dur); t = np.linspace(0, 1, n)
    f = 120 * (1 + 14 * t ** 2.2)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    ns = noise(n, 5) * t ** 2.5
    return (0.4 * tone + 0.6 * ns) * (t ** 1.6)


def whoosh(dur=0.6, **_):
    n = int(SR * dur); t = np.linspace(0, 1, n)
    x = noise(n, 6)
    cut = 300 + 5200 * np.sin(np.pi * t)
    out = np.zeros(n); y = 0.0
    for i in range(n):
        a = np.exp(-2 * np.pi * cut[i] / SR); y = (1 - a) * x[i] + a * y; out[i] = y
    return out * np.sin(np.pi * t) ** 1.5 * 2.2


def tick(dur=0.08, freq=1800, **_):
    n = int(SR * dur); t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 90)


def pop(dur=0.25, freq=520, **_):
    n = int(SR * dur); t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * (1 - 0.5 * t / dur) * t) * np.exp(-t * 22)


def drone(dur=6.0, freq=55, **_):
    n = int(SR * dur); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * freq * k * t + k) / k for k in (1, 2, 3)) * 0.4
    return x * np.minimum(t / 1.0, 1) * np.minimum((dur - t) / 1.0, 1)


def shimmer(dur=2.0, freq=1760, **_):
    n = int(SR * dur); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * freq * r * t) for r in (1, 1.5, 2.01)) / 3
    return x * np.exp(-t * 2.0) * (1 + 0.3 * np.sin(2 * np.pi * 6 * t))


KINDS = dict(impact=impact, riser=riser, whoosh=whoosh, tick=tick, pop=pop, drone=drone, shimmer=shimmer)


def render_events(events, duration):
    """Mistura os eventos e normaliza só se passar de 0.95 (evita clipping). Retorna float array."""
    mix = np.zeros(int(SR * duration) + SR * 3)
    for ev in events:
        kw = {k: v for k, v in ev.items() if k in ("dur", "freq")}
        s = KINDS[ev["type"]](**kw) * ev.get("gain", 0.8)
        i = int(ev["t"] * SR)
        mix[i:i + len(s)] += s[: len(mix) - i]
    mix = mix[: int(SR * duration)]
    peak = np.abs(mix).max()
    return mix / peak * 0.95 if peak > 0.95 else mix


def write_wav(mix, path):
    pcm = (mix * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", default="sfx.wav")
    a = ap.parse_args()
    mix = render_events(json.load(open(a.events)), a.duration)
    write_wav(mix, a.out)
    print(f"ok: {a.out} ({a.duration:.1f}s, pico final {np.abs(mix).max():.2f}; já limitado a 0.95, sem clipping)")


if __name__ == "__main__":
    main()
