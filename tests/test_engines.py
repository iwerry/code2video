"""Motores: sondas de disponibilidade reais, seleção e honestidade sobre o que foi testado."""
import json
import os
import unittest

from helpers import SK, copy_skill, run, write_json
import engines


class TestEngines(unittest.TestCase):
    def setUp(self):
        self.engs = engines.load_engines(SK)

    def test_every_executable_engine_has_probes_and_external_ones_do_not_claim_availability(self):
        for eid, e in self.engs.items():
            av = engines.availability(e)
            if e.get("external"):
                self.assertFalse(av["available"], eid)
                self.assertEqual(e["verification"]["state"], "planned", eid)
            else:
                self.assertTrue(e["availability"]["probes"], eid)

    def test_available_is_not_the_same_as_verified(self):
        """Motor só pode ser 'verified' se houver evidência de teste; os demais não podem fingir."""
        for eid, e in self.engs.items():
            if e["verification"]["state"] == "verified":
                self.assertTrue(e["verification"]["evidence"], eid)
        for eid in ("svg-gsap", "threejs", "remotion", "manim"):
            self.assertEqual(self.engs[eid]["verification"]["state"], "implemented-untested", eid)

    def test_remotion_not_reported_available_without_its_package(self):
        probes = {(p["kind"], p["name"]) for p in self.engs["remotion"]["availability"]["probes"]}
        self.assertIn(("node_package", "remotion"), probes)

    def test_probe_kinds(self):
        self.assertTrue(engines.probe({"kind": "binary", "name": "python3"}))
        self.assertFalse(engines.probe({"kind": "binary", "name": "binario-que-nao-existe-xyz"}))
        self.assertTrue(engines.probe({"kind": "python_module", "name": "json"}))
        self.assertFalse(engines.probe({"kind": "python_module", "name": "modulo_que_nao_existe_xyz"}))
        self.assertFalse(engines.probe({"kind": "node_package", "name": "pacote-que-nao-existe-xyz"}))
        self.assertTrue(engines.probe({"kind": "file", "name": SK}))

    def test_select_chooses_available_verified_engine(self):
        res, _ = engines.select(self.engs, "vertical-short", ["deterministic-seek", "audio"])
        if engines.availability(self.engs["canvas-motion-kit"])["available"]:
            self.assertEqual(res["id"], "canvas-motion-kit")
            self.assertIn("verified", res["reason"])

    def test_unavailable_engine_is_never_selected(self):
        sk = copy_skill()
        p = os.path.join(sk, "engines", "canvas-motion-kit", "engine.json")
        d = json.load(open(p)); d["availability"]["probes"].append({"kind": "binary", "name": "binario-inexistente-xyz"})
        write_json(p, d)
        res, info = engines.select(engines.load_engines(sk), "vertical-short", ["deterministic-seek"])
        self.assertIsNone(res)
        self.assertIn("binary:binario-inexistente-xyz", info["unavailable"]["canvas-motion-kit"])

    def test_cli_exit_codes(self):
        self.assertIn(run("engines.py", "select", "--project-type", "3d-realistic").returncode, (3,))
        r = run("engines.py", "select", "--project-type", "tipo-inexistente")
        self.assertEqual(r.returncode, 2); self.assertIn("Tipos conhecidos", r.stderr)
        r = run("engines.py", "detect", "--json")
        self.assertEqual(r.returncode, 0); self.assertIn("canvas-motion-kit", json.loads(r.stdout))

    def test_plan_only_message_for_external_engines(self):
        r = run("engines.py", "select", "--project-type", "3d-realistic")
        self.assertIn("apenas PLANO", r.stderr)


if __name__ == "__main__":
    unittest.main()
