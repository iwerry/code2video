"""Módulo production-automation: init/check/status/bundle sem precisar de render."""
import json
import os
import re
import shutil
import tempfile
import unittest

import helpers
from helpers import run, write_json


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.proj = os.path.join(self.d, "p")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def init(self, *extra):
        return run("pipeline.py", "init", self.proj, "--profile", "vertical-short", *extra)

    def test_init_creates_project_from_profile(self):
        r = self.init("--duration", 8)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = open(os.path.join(self.proj, "index.html"), encoding="utf-8").read()
        self.assertRegex(html, r"width:\s*1080")
        self.assertRegex(html, r"height:\s*1920")
        self.assertRegex(html, r"duration:\s*8")
        self.assertTrue(os.path.isfile(os.path.join(self.proj, "motion-kit.js")))

    def test_init_refuses_overwrite_and_bad_profile(self):
        self.assertEqual(self.init().returncode, 0)
        self.assertNotEqual(self.init().returncode, 0)
        r = run("pipeline.py", "init", os.path.join(self.d, "q"), "--profile", "nao-existe")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vertical-short", r.stderr)

    def test_check_passes_on_fresh_project(self):
        self.init("--duration", 8)
        r = run("pipeline.py", "check", self.proj)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_detects_script_duration_mismatch(self):
        self.init("--duration", 8)
        write_json(os.path.join(self.proj, "script.json"), {
            "title": "t", "duration_s": 12, "fps": 30, "status": "planned",
            "scenes": [{"name": "a", "start_s": 0, "end_s": 12, "purpose": "x", "visual": "x"}]})
        r = run("pipeline.py", "check", self.proj)
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, out)

    def test_bundle_refuses_without_real_render(self):
        self.init()
        r = run("pipeline.py", "bundle", self.proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("não", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.proj, "deliver")))

    def test_bundle_refuses_failed_report(self):
        self.init()
        write_json(os.path.join(self.proj, "out", "render-report.json"), {"ok": False})
        open(os.path.join(self.proj, "out", "video.mp4"), "wb").write(b"x")
        self.assertNotEqual(run("pipeline.py", "bundle", self.proj).returncode, 0)

    def test_inspect_without_video_fails_clearly(self):
        self.init()
        r = run("pipeline.py", "inspect", self.proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("renderize", r.stderr)

    def test_status_runs(self):
        self.init()
        r = run("pipeline.py", "status", self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("index.html", r.stdout)


if __name__ == "__main__":
    unittest.main()
