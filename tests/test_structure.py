"""Estrutura da skill, metadados, referências e CLIs."""
import ast
import glob
import os
import re
import unittest

from helpers import SK, REPO, SCRIPTS, run


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    text = read(path)
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md sem frontmatter"
    return dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M)), text


class TestSkillMetadata(unittest.TestCase):
    def test_frontmatter_name_and_trigger_preserved(self):
        fm, _ = frontmatter(os.path.join(SK, "SKILL.md"))
        self.assertEqual(fm["name"], "ai-motion-director")  # compatibilidade: nome não muda
        desc = fm["description"]
        self.assertLessEqual(len(desc), 1024)
        self.assertNotRegex(desc, r"[<>]")
        for trigger in ("vídeo", "animação", "motion graphics", "logo animado", "reel"):
            self.assertIn(trigger, desc, f"gatilho '{trigger}' sumiu da descrição")

    def test_core_is_small(self):
        n = len(read(os.path.join(SK, "SKILL.md")).splitlines())
        self.assertLessEqual(n, 150, "o Core (SKILL.md) deve continuar pequeno")

    def test_paths_mentioned_in_docs_exist(self):
        """Todo caminho `references/...`, `scripts/...` etc. citado em SKILL.md/referências existe."""
        docs = [os.path.join(SK, "SKILL.md")] + glob.glob(os.path.join(SK, "references", "*.md"))
        pat = re.compile(r"`((?:references|scripts|assets|examples|catalog|engines|modules|contracts|profiles|styles|prompt-profiles)/[\w./*-]+)`")
        missing = []
        for d in docs:
            for p in pat.findall(read(d)):
                p = p.rstrip(".,;:")
                if "*" in p or p.endswith("/"):
                    base = p.split("*")[0].rstrip("/")
                    ok = os.path.exists(os.path.join(SK, base))
                elif "<" in p:
                    continue
                else:
                    ok = os.path.exists(os.path.join(SK, p))
                if not ok:
                    missing.append(f"{os.path.relpath(d, SK)} → {p}")
        self.assertEqual(missing, [], "referências quebradas")

    def test_all_scripts_compile_and_have_help(self):
        for f in sorted(glob.glob(os.path.join(SCRIPTS, "*.py"))):
            with self.subTest(script=os.path.basename(f)):
                ast.parse(read(f))

    def test_cli_help_exit_zero(self):
        for s in ("render.py", "inspect_video.py", "audio_map.py", "synth_sfx.py", "contracts.py",
                  "registry.py", "catalog.py", "engines.py", "prompt_build.py", "pipeline.py"):
            with self.subTest(script=s):
                r = run(s, "--help")
                self.assertEqual(r.returncode, 0, r.stderr[-300:])

    def test_existing_cli_options_still_documented(self):
        """Regressão: as opções de linha de comando anteriores continuam existindo."""
        r = run("render.py", "--help").stdout
        for opt in ("--fps", "--audio", "--blur", "--shutter", "--start", "--end", "--crf", "--still",
                    "--keep-frames", "--capture", "--loudnorm"):
            self.assertIn(opt, r, f"render.py perdeu {opt}")
        r = run("inspect_video.py", "--help").stdout
        for opt in ("--sheet", "--cols", "--thumb", "--times", "--count"):
            self.assertIn(opt, r, f"inspect_video.py perdeu {opt}")

    def test_template_and_examples_preserved(self):
        for f in ("assets/template/index.html", "assets/template/motion-kit.js",
                  "examples/short-vertical-dado.md", "examples/logo-briefing-incompleto.md"):
            self.assertTrue(os.path.isfile(os.path.join(SK, f)), f"{f} sumiu")
        kit = read(os.path.join(SK, "assets/template/motion-kit.js"))
        for fn in ("kinetic", "trim", "spring", "shake", "particles", "morph", "plane", "runScenes", "fontsReady", "halo", "fmtInt"):
            self.assertIn(fn, kit, f"motion-kit perdeu {fn}")
        html = read(os.path.join(SK, "assets/template/index.html"))
        for tok in ("window.__meta", "window.__seek", "window.__ready", "window.__canvas", "window.__sfx"):
            self.assertIn(tok, html)

    def test_license_and_readme_present(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, "LICENSE")))
        self.assertTrue(os.path.isfile(os.path.join(REPO, "README.md")))


if __name__ == "__main__":
    unittest.main()
