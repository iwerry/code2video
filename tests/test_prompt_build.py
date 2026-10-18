"""Engenharia de prompts: separação decisão×ferramenta, avisos e rejeição de entrada inválida."""
import json
import os
import tempfile
import unittest

from helpers import SK, run, write_json
import prompt_build

SHOT = {"id": "plano-3", "subject": "mãos organizando post-its", "action": "colando notas num quadro branco",
        "environment": "escritório claro", "framing": "close", "camera_motion": "push-in lento",
        "lighting": "luz de janela lateral, quente", "atmosphere": "documental", "duration_s": 4, "aspect": "9:16",
        "profile": "generic-video"}


class TestPromptBuild(unittest.TestCase):
    def setUp(self):
        self.profs = prompt_build.load_profiles(SK)

    def test_builds_prompt_with_all_given_fields_and_generated_status(self):
        p, w = prompt_build.build(SHOT, self.profs["generic-video"])
        for frag in ("mãos organizando post-its", "close", "luz de janela lateral", "documental", "4 s", "9:16"):
            self.assertIn(frag, p)
        self.assertNotIn("{", p)

    def test_unverified_profile_warns(self):
        _, w = prompt_build.build(SHOT, self.profs["generic-video"])
        self.assertTrue(any("NÃO verificadas" in x for x in w))

    def test_incompatible_camera_instructions_warn(self):
        _, w = prompt_build.build(dict(SHOT, camera_motion="câmera fixa com push-in intenso"), self.profs["generic-video"])
        self.assertTrue(any("estática e movimento" in x for x in w))
        _, w = prompt_build.build(SHOT, self.profs["generic-video"])
        self.assertFalse(any("estática e movimento" in x for x in w))

    def test_text_in_image_warning_when_tool_support_unconfirmed(self):
        _, w = prompt_build.build(dict(SHOT, subject='placa com o texto "PROMO"'), self.profs["generic-video"])
        self.assertTrue(any("componha o texto por código" in x for x in w))

    def test_missing_optional_fields_are_dropped_cleanly(self):
        shot = {k: v for k, v in SHOT.items() if k not in ("environment", "lighting", "atmosphere", "camera_motion")}
        p, _ = prompt_build.build(shot, self.profs["generic-video"])
        self.assertNotIn("Luz:", p); self.assertNotIn("Câmera:", p); self.assertNotIn(",,", p)

    def test_long_prompt_warns(self):
        p, w = prompt_build.build(dict(SHOT, action="palavra " * 150), self.profs["generic-video"])
        self.assertTrue(any("excede o limite" in x for x in w))

    def test_cli_rejects_invalid_shot_and_unknown_profile(self):
        d = tempfile.mkdtemp()
        write_json(os.path.join(d, "ok.json"), SHOT)
        write_json(os.path.join(d, "bad.json"), {"id": "x", "subject": "só isso"})
        r = run("prompt_build.py", "--shot", os.path.join(d, "bad.json"), "--profile", "generic-video")
        self.assertEqual(r.returncode, 1); self.assertIn("campo obrigatório ausente", r.stderr)
        r = run("prompt_build.py", "--shot", os.path.join(d, "ok.json"), "--profile", "inexistente")
        self.assertEqual(r.returncode, 2); self.assertIn("Disponíveis", r.stderr)
        r = run("prompt_build.py", "--shot", os.path.join(d, "ok.json"), "--profile", "generic-video", "--json")
        out = json.loads(r.stdout); self.assertEqual(out["status"], "generated")

    def test_shipped_profiles_never_claim_verification(self):
        for pid, p in self.profs.items():
            self.assertFalse(p["capabilities_verified"], f"{pid}: perfil genérico não pode alegar capacidades verificadas")


if __name__ == "__main__":
    unittest.main()
