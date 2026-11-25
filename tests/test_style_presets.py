import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'ai-motion-director'

class StylePresetsTest(unittest.TestCase):
    def test_presets(self):
        styles = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'styles').glob('*.json')]
        self.assertGreaterEqual(len(styles), 10)
        self.assertEqual(len(styles), len({s['id'] for s in styles}))
        for style in styles:
            for key in ('bg', 'ink', 'accent'):
                self.assertRegex(style['palette'][key], r'^#[0-9a-fA-F]{6}$')
