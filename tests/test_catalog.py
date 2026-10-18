"""Catálogo de técnicas: busca por facetas e evolução sem tocar no Core (caso 1)."""
import json
import os
import unittest

from helpers import SK, copy_skill, run, sha, write_json
import catalog

NEW_TECH = {
    "id": "teste-tecnica-nova", "name": "Técnica de teste", "category": "foundations",
    "narrative_intents": ["hook"], "emotions": ["surprise"], "motion_type": "transform", "contexts": ["short-social"],
    "complexity": 1, "feasibility": "A", "engines": ["canvas-motion-kit"], "requirements": "Canvas",
    "when_to_use": "no teste", "why": "prova a extensibilidade", "risks": ["nenhum"], "alternatives": ["nenhuma"]}


class TestCatalogContent(unittest.TestCase):
    def test_catalog_valid_and_complete(self):
        self.assertEqual(catalog.check(SK), [])
        techs = catalog.load_all(SK)
        self.assertGreaterEqual(len(techs), 62, "o catálogo original tinha 62 técnicas")
        self.assertEqual(len({t["id"] for t in techs}), len(techs))

    def test_feasibility_matches_reality_of_engine(self):
        """Técnica A só pode depender do motor canvas-motion-kit (testado); C só de motores externos/Three/DCC."""
        for t in catalog.load_all(SK):
            if t["feasibility"] == "A":
                self.assertIn("canvas-motion-kit", t["engines"], t["id"])
            if t["feasibility"] == "C":
                self.assertNotIn("canvas-motion-kit", t["engines"], t["id"])

    def test_search_by_intent_emotion_context(self):
        res = catalog.search(catalog.load_all(SK), intent=["impact"], emotion=["surprise"], context=["short-social"], feasible="A")
        ids = [t["id"] for t in res]
        self.assertIn("impact-shake-flash", ids)
        self.assertNotIn("fluid-dynamic-simulation", ids)

    def test_search_filters_complexity_engine_text(self):
        techs = catalog.load_all(SK)
        simple = catalog.search(techs, max_complexity=1)
        self.assertTrue(simple and all(t["complexity"] <= 1 for t in simple))
        self.assertTrue(all("ffmpeg-post" in t["engines"] for t in catalog.search(techs, engine=["ffmpeg-post"])))
        self.assertTrue(any(t["id"] == "trim-paths" for t in catalog.search(techs, text="contornos")))

    def test_ranking_prefers_simple_and_feasible(self):
        res = catalog.search(catalog.load_all(SK), intent=["reveal"])
        keys = [(t["complexity"], catalog.FEAS_RANK[t["feasibility"]]) for t in res]
        self.assertEqual(keys, sorted(keys))

    def test_cli_search_and_show(self):
        r = run("catalog.py", "search", "--intent", "hook,impact", "--feasible", "A", "--limit", "3")
        self.assertEqual(r.returncode, 0); self.assertIn("técnica(s)", r.stdout)
        self.assertEqual(run("catalog.py", "show", "particle-systems").returncode, 0)
        r = run("catalog.py", "show", "particle")
        self.assertEqual(r.returncode, 2); self.assertIn("parecidas", r.stderr)


class TestExtensibility(unittest.TestCase):
    def test_new_technique_without_modifying_core(self):
        """Caso 1: uma nova técnica entra só soltando um arquivo; o Core e os manifestos ficam byte a byte iguais."""
        sk = copy_skill()
        guarded = [os.path.join(sk, "SKILL.md"), os.path.join(sk, "core", "core.json")] + \
                  [os.path.join(sk, "modules", m, "module.json") for m in os.listdir(os.path.join(sk, "modules"))]
        before = {p: sha(p) for p in guarded}
        write_json(os.path.join(sk, "catalog", "techniques", "extra", "minha.json"), [NEW_TECH])
        self.assertEqual(catalog.check(sk), [])
        found = catalog.search(catalog.load_all(sk), intent=["hook"], emotion=["surprise"], context=["short-social"])
        self.assertIn("teste-tecnica-nova", [t["id"] for t in found])
        r = run("registry.py", "check", "--skill-dir", sk)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(before, {p: sha(p) for p in guarded}, "o Core ou um manifesto foi alterado")

    def test_invalid_technique_rejected_with_location(self):
        sk = copy_skill()
        bad = dict(NEW_TECH, complexity=9, category="inventada")
        write_json(os.path.join(sk, "catalog", "techniques", "ruim.json"), [bad])
        errs = catalog.check(sk)
        joined = " | ".join(errs)
        self.assertIn("ruim.json[0] (teste-tecnica-nova)", joined)
        self.assertIn("> máximo 5", joined)
        self.assertIn("valor 'inventada' inválido", joined)

    def test_duplicate_id_and_unknown_engine_rejected(self):
        sk = copy_skill()
        write_json(os.path.join(sk, "catalog", "techniques", "dup.json"), [NEW_TECH, dict(NEW_TECH)])
        self.assertTrue(any("id duplicado" in e for e in catalog.check(sk)))
        sk2 = copy_skill()
        write_json(os.path.join(sk2, "catalog", "techniques", "e.json"), [dict(NEW_TECH, engines=["motor-fantasma"])])
        r = run("registry.py", "check", "--skill-dir", sk2)
        self.assertEqual(r.returncode, 1); self.assertIn("motor inexistente 'motor-fantasma'", r.stdout)


if __name__ == "__main__":
    unittest.main()
