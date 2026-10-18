"""Ponta a ponta REAL: Playwright + Chromium + FFmpeg. Pula (skip, não passa) se a pilha não existir."""
import json
import os
import shutil
import tempfile
import unittest

import helpers
from helpers import run, ffprobe, have_render_stack, write_json, SK
import contracts

MINI = """<!doctype html><meta charset=utf-8><body style="margin:0"><canvas id=c width=320 height=180></canvas>
<script>
const META = { width: 320, height: 180, duration: 1, fps: 10 };
window.__meta = META; window.__canvas = document.getElementById('c');
const ctx = window.__canvas.getContext('2d');
window.__seek = (t) => { ctx.fillStyle = '#103'; ctx.fillRect(0,0,320,180); ctx.fillStyle = '#fc0'; ctx.fillRect(t*250, 70, 40, 40); };
window.__sfx = [{ t: 0.3, type: 'impact' }];
%s
</script>"""


@unittest.skipUnless(have_render_stack(), "pilha de render (playwright+chromium+ffmpeg) indisponível")
class TestRenderE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.proj = os.path.join(cls.d, "mini")
        assert run("pipeline.py", "init", cls.proj, "--profile", "landscape-brand", "--duration", 1).returncode == 0
        open(os.path.join(cls.proj, "index.html"), "w").write(MINI % "window.__ready = true;")
        cls.r = run("pipeline.py", "render", cls.proj, timeout=240)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_render_succeeds_and_video_matches_page_meta(self):
        self.assertEqual(self.r.returncode, 0, self.r.stdout + self.r.stderr)
        info = ffprobe(os.path.join(self.proj, "out", "video.mp4"))
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual((v["width"], v["height"]), (320, 180))
        self.assertAlmostEqual(float(info["format"]["duration"]), 1.0, delta=0.15)
        self.assertTrue(any(s["codec_type"] == "audio" for s in info["streams"]), "__sfx deveria virar áudio")

    def test_report_is_valid_and_has_evidence(self):
        p = os.path.join(self.proj, "out", "render-report.json")
        self.assertEqual(contracts.validate_file("execution-report", p), [])
        rep = json.load(open(p))
        self.assertTrue(rep["ok"])
        self.assertEqual(rep["frames"], 10)
        self.assertEqual(rep["audio"], "synth-sfx")
        self.assertTrue(rep["evidence"])

    def test_inspect_is_technical_and_never_validated(self):
        r = run("pipeline.py", "inspect", self.proj, "--count", 4, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        qa = os.path.join(self.proj, "out", "qa-technical.json")
        self.assertEqual(contracts.validate_file("qa-report", qa), [])
        data = json.load(open(qa))
        self.assertEqual(data["kind"], "technical")
        self.assertNotEqual(data["status"], "validated")
        self.assertTrue(os.path.isfile(os.path.join(self.proj, "out", "folha.png")))

    def test_bundle_after_real_render(self):
        run("pipeline.py", "inspect", self.proj, "--count", 3, timeout=120)
        r = run("pipeline.py", "bundle", self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        man = json.load(open(os.path.join(self.proj, "deliver", "MANIFEST.json")))
        names = {f["name"] for f in man["files"]}
        self.assertIn("video.mp4", names)
        self.assertIn("AUSENTE", man["creative_review"])  # sem avaliação criativa, o pacote diz isso

    def test_render_without_ready_fails_with_report(self):
        proj = os.path.join(self.d, "noready")
        run("pipeline.py", "init", proj, "--profile", "landscape-brand", "--duration", 1)
        open(os.path.join(proj, "index.html"), "w").write(MINI % "")
        rep = os.path.join(proj, "out", "r.json")
        r = run("render.py", os.path.join(proj, "index.html"), os.path.join(proj, "out", "v.mp4"),
                "--report", rep, timeout=120)  # espera 30 s pelo __ready
        self.assertNotEqual(r.returncode, 0)
        data = json.load(open(rep))
        self.assertFalse(data["ok"])
        self.assertIn("__ready", data["errors"][0])
        self.assertEqual(contracts.validate_file("execution-report", rep), [])
        self.assertFalse(os.path.exists(os.path.join(proj, "out", "v.mp4")))

    def test_real_template_still_and_legacy_cli_without_report(self):
        proj = os.path.join(self.d, "tpl")
        run("pipeline.py", "init", proj, "--profile", "square-social", "--duration", 4)
        png = os.path.join(self.d, "t.png")
        r = run("render.py", os.path.join(proj, "index.html"), png, "--still", 2, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertGreater(os.path.getsize(png), 5000)
        self.assertNotIn("relatório:", r.stdout)  # CLI antigo (sem --report) segue idêntico


if __name__ == "__main__":
    unittest.main()
