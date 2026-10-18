"""Arquitetura modular: registro, dependências, evolução independente e degradação graciosa (casos 2, 3, 4)."""
import json
import os
import shutil
import unittest

from helpers import SK, copy_skill, run, sha, write_json
import contracts
import engines
import registry


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class TestRegistry(unittest.TestCase):
    def test_repository_architecture_is_valid(self):
        errs, mods, engs = registry.check(SK)
        self.assertEqual(errs, [])
        self.assertEqual(set(mods), {"creative-intelligence", "narrative-intelligence", "motion-graphics-intelligence",
                                     "prompt-engineering", "production-engines", "audio-rhythm", "quality-assurance",
                                     "production-automation"})
        self.assertGreaterEqual(len(engs), 8)

    def test_no_circular_dependencies(self):
        self.assertIsNone(registry.find_cycle({m: d["depends_on"] for m, (_, d) in registry.discover(SK)[0].items()}))
        self.assertEqual(registry.find_cycle({"a": ["b"], "b": ["c"], "c": ["a"]}), ["a", "b", "c", "a"])

    def test_verified_modules_point_to_real_tests(self):
        for mid, (_, d) in registry.discover(SK)[0].items():
            if d["verification"]["state"] == "verified":
                self.assertTrue(d["verification"]["evidence"], mid)
                for ev in d["verification"]["evidence"]:
                    self.assertTrue(os.path.exists(os.path.join(os.path.dirname(SK), ev)), f"{mid}: {ev}")

    def test_broken_manifests_detected(self):
        sk = copy_skill()
        p = os.path.join(sk, "modules", "audio-rhythm", "module.json")
        d = load(p); d["docs"].append("references/nao-existe.md"); d["depends_on"] = ["fantasma"]; d["consumes"] = ["contrato-fantasma"]
        d["core_contract"] = 2
        write_json(p, d)
        out = run("registry.py", "check", "--skill-dir", sk).stdout
        for frag in ("'references/nao-existe.md', que não existe", "módulo inexistente 'fantasma'",
                     "contrato inexistente 'contrato-fantasma'", "core_contract=2"):
            self.assertIn(frag, out)

    def test_cycle_detected_in_manifests(self):
        sk = copy_skill()
        for m, dep in (("audio-rhythm", "quality-assurance"), ("quality-assurance", "audio-rhythm")):
            p = os.path.join(sk, "modules", m, "module.json"); d = load(p); d["depends_on"] = [dep]; write_json(p, d)
        self.assertIn("dependência circular", run("registry.py", "check", "--skill-dir", sk).stdout)

    def test_core_must_stay_small_and_know_every_module(self):
        sk = copy_skill()
        p = os.path.join(sk, "SKILL.md")
        text = load_text(p)
        open(p, "w", encoding="utf-8").write(text.replace("`prompt-engineering`", "`xxxx`"))
        self.assertIn("não cita o módulo `prompt-engineering`", run("registry.py", "check", "--skill-dir", sk).stdout)
        open(p, "w", encoding="utf-8").write(text + "\nlinha\n" * 200)
        self.assertIn("o Core deve ficar pequeno", run("registry.py", "check", "--skill-dir", sk).stdout)

    def test_new_module_needs_only_a_folder_plus_core_mention(self):
        sk = copy_skill()
        m = load(os.path.join(sk, "modules", "audio-rhythm", "module.json"))
        m.update(id="modulo-novo", name="Novo", scripts=[], docs=["references/audio-rhythm.md"], depends_on=[], verification={"state": "planned"})
        write_json(os.path.join(sk, "modules", "modulo-novo", "module.json"), m)
        out = run("registry.py", "check", "--skill-dir", sk).stdout
        self.assertIn("não cita o módulo `modulo-novo`", out)  # único pedido: o Core precisa conhecer o contrato
        p = os.path.join(sk, "SKILL.md"); open(p, "a", encoding="utf-8").write("\n`modulo-novo`\n")
        self.assertEqual(run("registry.py", "check", "--skill-dir", sk).returncode, 0)


def load_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class TestIndependentEvolution(unittest.TestCase):
    def test_narrative_module_evolves_without_touching_engines(self):
        """Caso 2: mudar a narrativa (doc + versão) não altera nenhum arquivo de motor, de script de render nem do Core."""
        sk = copy_skill()
        guarded = [os.path.join(sk, "scripts", f) for f in ("render.py", "engines.py", "pipeline.py")] + \
                  [os.path.join(sk, "engines", e, "engine.json") for e in os.listdir(os.path.join(sk, "engines"))] + \
                  [os.path.join(sk, "SKILL.md"), os.path.join(sk, "core", "core.json")]
        before = {p: sha(p) for p in guarded}
        doc = os.path.join(sk, "references", "narrative-emotion.md")
        open(doc, "a", encoding="utf-8").write("\n## Nova estrutura: trailer em 3 batidas\n")
        p = os.path.join(sk, "modules", "narrative-intelligence", "module.json")
        d = load(p); d["version"] = "1.1.0"; write_json(p, d)
        self.assertEqual(run("registry.py", "check", "--skill-dir", sk).returncode, 0)
        self.assertEqual(before, {p: sha(p) for p in guarded})
        res, _ = engines.select(engines.load_engines(sk), "vertical-short", ["audio"])
        self.assertEqual(res["id"], "canvas-motion-kit")

    def test_engine_can_be_replaced_without_rewriting_the_script(self):
        """Caso 3: o mesmo roteiro continua válido e planejável se o motor padrão sai; troca-se só o plano."""
        script = load(os.path.join(SK, "examples", "short-vertical-dado", "script.json"))
        sk = copy_skill()
        shutil.rmtree(os.path.join(sk, "engines", "canvas-motion-kit"))
        # roteiro não referencia motor algum: segue válido
        self.assertEqual(contracts.validate("script", script), [])
        # um motor substituto declarado só por manifesto passa a atender o mesmo tipo de projeto
        sub = load(os.path.join(SK, "engines", "svg-gsap", "engine.json"))
        sub.update(id="motor-substituto", project_types=["vertical-short"], capabilities=["deterministic-seek", "audio"],
                   availability={"probes": [{"kind": "binary", "name": "python3"}]},
                   verification={"state": "implemented-untested"})
        write_json(os.path.join(sk, "engines", "motor-substituto", "engine.json"), sub)
        res, _ = engines.select(engines.load_engines(sk), "vertical-short", ["deterministic-seek", "audio"])
        self.assertEqual(res["id"], "motor-substituto")
        plan = {"engine": {"id": res["id"], "reason": res["reason"]}, "profile": "vertical-short", "status": "planned",
                "steps": [{"name": "render", "action": "renderizar com o motor substituto"}]}
        self.assertEqual(contracts.validate("production-plan", plan), [])

    def test_prompt_tool_change_does_not_touch_narrative_or_core(self):
        """Trocar a ferramenta de geração = outro perfil; shot-spec e Core não mudam."""
        sk = copy_skill()
        guarded = [os.path.join(sk, "SKILL.md"), os.path.join(sk, "references", "narrative-emotion.md")]
        before = {p: sha(p) for p in guarded}
        prof = load(os.path.join(sk, "prompt-profiles", "generic-video.json"))
        prof.update(id="ferramenta-x", name="Ferramenta X", max_prompt_words=60)
        write_json(os.path.join(sk, "prompt-profiles", "ferramenta-x.json"), prof)
        self.assertEqual(run("registry.py", "check", "--skill-dir", sk).returncode, 0)
        self.assertEqual(before, {p: sha(p) for p in guarded})


class TestOptionalIntegrations(unittest.TestCase):
    def test_every_integration_declares_a_fallback(self):
        n = 0
        for mid, (_, d) in registry.discover(SK)[0].items():
            for i in d.get("optional_integrations", []):
                self.assertTrue(i["fallback"].strip(), f"{mid}/{i['skill']}")
                n += 1
        self.assertGreaterEqual(n, 3)

    def test_unavailable_integration_does_not_block_core_flow(self):
        """Caso 4: com a Skill externa indisponível, o handoff vira 'unavailable' e o fluxo básico segue."""
        handoff = {"from": "ai-motion-director", "to": "dataviz", "task": "paleta para contador", "inputs": {},
                   "expected_output": {"contract": "style-alias"}, "fallback": "usar styles/punchy-social.json", "status": "unavailable"}
        self.assertEqual(contracts.validate("handoff", handoff), [])
        # o fallback existe de verdade e cumpre o contrato esperado
        self.assertTrue(os.path.isfile(os.path.join(SK, "styles", "punchy-social.json")))
        self.assertEqual(contracts.validate_file("style-alias", os.path.join(SK, "styles", "punchy-social.json")), [])
        # e a arquitetura continua válida mesmo sem nenhuma integração presente no ambiente
        self.assertEqual(run("registry.py", "check").returncode, 0)

    def test_missing_optional_engine_dependencies_degrade_gracefully(self):
        """Motores sem dependências instaladas aparecem como indisponíveis; a seleção usa o que existe."""
        engs = engines.load_engines(SK)
        for eid in ("threejs", "svg-gsap", "manim"):
            av = engines.availability(engs[eid])
            self.assertIn(av["available"], (True, False))  # nunca levanta exceção
        res, info = engines.select(engs, "vertical-short", ["audio"])
        self.assertIsNotNone(res)

    def test_handoff_rejects_invalid_status(self):
        h = {"from": "a", "to": "b", "task": "t", "inputs": {}, "expected_output": {"contract": "x"}, "status": "talvez"}
        self.assertTrue(contracts.validate("handoff", h))


if __name__ == "__main__":
    unittest.main()
