"""Módulo audio-rhythm: síntese determinística e mapa de áudio com dados reais."""
import json
import os
import shutil
import tempfile
import unittest

import helpers
from helpers import run, sha


@unittest.skipUnless(helpers.has_module("numpy"), "numpy ausente")
class TestSynth(unittest.TestCase):
    EVENTS = [{"t": 0.2, "type": "impact"}, {"t": 1.0, "type": "tick"}, {"t": 1.5, "type": "pop", "gain": 1.0},
              {"t": 0.0, "type": "riser", "dur": 1.0}]

    def test_deterministic_and_no_clipping(self):
        import synth_sfx
        a = synth_sfx.render_events(self.EVENTS, 3)
        b = synth_sfx.render_events(self.EVENTS, 3)
        self.assertTrue((a == b).all(), "mesma lista de eventos deve gerar o mesmo áudio")
        self.assertLessEqual(abs(a).max(), 0.95 + 1e-9)
        self.assertGreater(abs(a).max(), 0.05, "áudio não deve ser silêncio")

    def test_cli_writes_wav(self):
        d = tempfile.mkdtemp()
        ev = os.path.join(d, "e.json")
        json.dump(self.EVENTS, open(ev, "w"))
        r = run("synth_sfx.py", "--events", ev, "--duration", 3, "--out", os.path.join(d, "s.wav"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(os.path.getsize(os.path.join(d, "s.wav")), 40000)
        shutil.rmtree(d)


@unittest.skipUnless(helpers.has_module("numpy") and shutil.which("ffmpeg"), "numpy/ffmpeg ausentes")
class TestAudioMap(unittest.TestCase):
    def test_onsets_near_known_events(self):
        import synth_sfx
        d = tempfile.mkdtemp()
        events = [{"t": 1.0, "type": "impact"}, {"t": 2.5, "type": "impact"}]
        wav = os.path.join(d, "a.wav")
        synth_sfx.write_wav(synth_sfx.render_events(events, 4), wav)
        out = os.path.join(d, "a.json")
        r = run("audio_map.py", wav, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.load(open(out))
        for k in ("duration", "fps", "rms", "onsets", "bpm_estimate"):
            self.assertIn(k, data)
        self.assertAlmostEqual(data["duration"], 4, delta=0.1)
        for ev in events:
            self.assertTrue(any(abs(o - ev["t"]) < 0.15 for o in data["onsets"]),
                            f"nenhum onset perto de {ev['t']}s: {data['onsets']}")
        self.assertIsNone(data["bpm_estimate"], "áudio curto não deve inventar BPM")
        shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
