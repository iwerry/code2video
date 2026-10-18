"""Contratos entre módulos: aceitam o certo, rejeitam o errado de forma compreensível."""
import copy
import glob
import json
import os
import unittest

from helpers import SK, run, write_json
import contracts
import tempfile

GOOD_SCRIPT = {"title": "t", "format": "9:16", "fps": 24, "duration_s": 8, "status": "planned", "scenes": [
    {"name": "a", "start_s": 0, "end_s": 3.25, "narrative_goal": "g", "emotion": "e", "visual": "v"},
    {"name": "b", "start_s": 3.25, "end_s": 8, "narrative_goal": "g", "emotion": "e", "visual": "v"}]}


class TestSchemas(unittest.TestCase):
    def test_every_schema_loads_and_refs_resolve(self):
        for name in contracts.list_contracts():
            with self.subTest(contract=name):
                schema = contracts.load_schema(name)
                self.assertIn("title", schema)

                def refs(node):
                    if isinstance(node, dict):
                        if "$ref" in node:
                            contracts._resolve(node["$ref"], schema, name)  # levanta KeyError se quebrado
                        for v in node.values():
                            refs(v)
                    elif isinstance(node, list):
                        for v in node:
                            refs(v)
                refs(schema)


class TestValidation(unittest.TestCase):
    def test_valid_script(self):
        self.assertEqual(contracts.validate("script", GOOD_SCRIPT), [])

    def test_invalid_inputs_are_rejected_with_readable_messages(self):
        bad = {"title": 1}
        msgs = " | ".join(contracts.validate("script", bad))
        self.assertIn("campo obrigatório ausente: 'scenes'", msgs)
        self.assertIn("title: esperado string", msgs)

    def test_enum_and_unknown_field_messages(self):
        s = copy.deepcopy(GOOD_SCRIPT); s["format"] = "5:4"; s["extra"] = 1
        msgs = " | ".join(contracts.validate("script", s))
        self.assertIn("valor '5:4' inválido; permitidos:", msgs)
        self.assertIn("campo desconhecido 'extra'", msgs)

    def test_unknown_contract_lists_available(self):
        with self.assertRaises(contracts.ContractError) as cm:
            contracts.validate("nao-existe", {})
        self.assertIn("Disponíveis:", str(cm.exception))

    def test_temporal_consistency_gap(self):
        s = copy.deepcopy(GOOD_SCRIPT); s["scenes"][1]["start_s"] = 3.6
        self.assertTrue(any("deveria começar em 3.250s" in m for m in contracts.validate("script", s)))

    def test_temporal_consistency_total(self):
        s = copy.deepcopy(GOOD_SCRIPT); s["duration_s"] = 9
        self.assertTrue(any("soma das cenas termina em 8s" in m for m in contracts.validate("script", s)))

    def test_declared_overlap_is_allowed(self):
        s = copy.deepcopy(GOOD_SCRIPT); s["scenes"][1]["start_s"] = 3.0; s["scenes"][1]["overlap_s"] = 0.25
        self.assertEqual(contracts.validate("script", s), [])

    def test_motion_longer_than_scene_rejected(self):
        s = copy.deepcopy(GOOD_SCRIPT)
        s["scenes"][0]["motions"] = [{"what": "x", "duration_s": 5}]
        self.assertTrue(any("dura 5s e a cena só 3.25s" in m for m in contracts.validate("script", s)))

    def test_cue_outside_scene_rejected(self):
        s = copy.deepcopy(GOOD_SCRIPT); s["scenes"][0]["cues"] = [{"t": 5, "type": "impact"}]
        self.assertTrue(any("fora da cena" in m for m in contracts.validate("script", s)))

    def test_bad_json_file_message(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "x.json"); open(p, "w").write("{oops")
        msgs = contracts.validate_file("script", p)
        self.assertIn("JSON inválido", msgs[0])

    def test_cli_exit_codes(self):
        d = tempfile.mkdtemp()
        write_json(os.path.join(d, "ok.json"), GOOD_SCRIPT)
        write_json(os.path.join(d, "bad.json"), {"title": 1})
        self.assertEqual(run("contracts.py", "validate", "script", os.path.join(d, "ok.json")).returncode, 0)
        r = run("contracts.py", "validate", "script", os.path.join(d, "bad.json"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("INVÁLIDO", r.stdout)
        self.assertEqual(run("contracts.py", "validate", "zzz", os.path.join(d, "ok.json")).returncode, 2)


class TestRecommendationVsExecution(unittest.TestCase):
    """Caso 6: resultados de execução são diferenciados de recomendações não executadas."""

    def test_executed_requires_evidence_anywhere(self):
        rec = {"items": [{"technique_id": "particle-systems", "narrative_goal": "g", "expected_effect": "e", "moment": "m",
                          "justification": "j", "simpler_alternative": "s"}], "status": "executed"}
        errs = contracts.validate("technique-recommendation", rec)
        self.assertTrue(any("exige 'evidence'" in e for e in errs), errs)
        rec["status"] = "recommended"
        self.assertEqual(contracts.validate("technique-recommendation", rec), [])

    def test_validated_with_evidence_ok(self):
        rec = {"kind": "creative", "target": "video.mp4", "findings": [], "status": "validated",
               "evidence": [{"type": "frame", "ref": "folha.png"}]}
        self.assertEqual(contracts.validate("qa-report", rec), [])
        del rec["evidence"]
        self.assertTrue(contracts.validate("qa-report", rec))

    def test_nested_step_claiming_executed_without_proof_rejected(self):
        plan = {"engine": {"id": "canvas-motion-kit", "reason": "r"}, "profile": "vertical-short", "status": "planned",
                "steps": [{"name": "render", "action": "renderizar", "status": "executed"}]}
        self.assertTrue(any("steps[0]" in e for e in contracts.validate("production-plan", plan)))

    def test_failed_execution_must_explain(self):
        rep = {"tool": "render.py", "command": "c", "started_at": "x", "ok": False, "outputs": [], "status": "executed",
               "evidence": [{"type": "log", "ref": "traceback"}]}
        self.assertTrue(any("'errors'" in e for e in contracts.validate("execution-report", rep)))

    def test_technical_and_creative_qa_are_separate_kinds(self):
        for kind in ("technical", "creative"):
            self.assertEqual(contracts.validate("qa-report", {"kind": kind, "target": "t", "findings": [], "status": "planned"}), [])
        self.assertTrue(contracts.validate("qa-report", {"kind": "estetico", "target": "t", "findings": [], "status": "planned"}))


class TestExamplesAreValid(unittest.TestCase):
    def test_example_artifacts_pass_contracts(self):
        n = 0
        for d in sorted(glob.glob(os.path.join(SK, "examples", "*"))):
            if os.path.isdir(d):
                r = run("contracts.py", "check-dir", d)
                self.assertEqual(r.returncode, 0, f"{d}\n{r.stdout}")
                n += 1
        self.assertGreaterEqual(n, 2)

    def test_example_techniques_exist_in_catalog(self):
        import catalog
        ids = {t["id"] for t in catalog.load_all()}
        for f in glob.glob(os.path.join(SK, "examples", "*", "*.json")):
            d = json.load(open(f, encoding="utf-8"))
            used = [x for sc in d.get("scenes", []) for x in sc.get("techniques", [])] + \
                   [i["technique_id"] for i in d.get("items", [])] if isinstance(d, dict) else []
            for t in used:
                self.assertIn(t, ids, f"{os.path.basename(os.path.dirname(f))}/{os.path.basename(f)} cita técnica inexistente '{t}'")


if __name__ == "__main__":
    unittest.main()
