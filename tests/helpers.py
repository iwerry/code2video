"""Utilidades compartilhadas pelos testes (somente biblioteca padrão)."""
import warnings
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

warnings.simplefilter("ignore", ResourceWarning)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(REPO, "ai-motion-director")
SCRIPTS = os.path.join(SK, "scripts")
sys.path.insert(0, SCRIPTS)


def run(script, *args, cwd=None, timeout=300):
    """Executa um script da skill como o usuário faria (CLI real). Retorna CompletedProcess."""
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                          capture_output=True, text=True, cwd=cwd, timeout=timeout)


def copy_skill():
    """Cópia descartável da skill, para testar evolução sem mexer no repositório."""
    d = tempfile.mkdtemp(prefix="amd-skill-")
    dst = os.path.join(d, "ai-motion-director")
    shutil.copytree(SK, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def has_module(name):
    return importlib.util.find_spec(name) is not None


def have_render_stack():
    """Playwright + Chromium + FFmpeg + numpy + PIL disponíveis? (testes de render pulam se não)."""
    if not (has_module("playwright") and has_module("numpy") and has_module("PIL")):
        return False
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False
    import engines
    return engines._playwright_chromium()


def ffprobe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(out)
