"""The README image is generated, not screenshotted.

If these fail after an engine change, rerun `python scripts/render_demo_svg.py`
rather than editing the SVG by hand.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "assets" / "demo.svg"


def _load():
    spec = importlib.util.spec_from_file_location(
        "render_demo_svg", ROOT / "scripts" / "render_demo_svg.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDemoAsset(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_shipped_svg_matches_a_fresh_render(self):
        shipped = SVG.read_text(encoding="utf-8")
        self.assertTrue(shipped == self.mod.build())

    def test_render_is_deterministic(self):
        self.assertTrue(self.mod.build() == self.mod.build())

    def test_render_contains_the_real_decision_not_a_mock(self):
        svg = self.mod.build()
        self.assertTrue("TRAFFIC" in svg)
        self.assertTrue("AUTO" in svg and "FENCE" in svg and "HOLD" in svg)
        self.assertTrue("uncovered" in svg)

    def test_render_is_valid_xml(self):
        import xml.etree.ElementTree as ET

        ET.fromstring(SVG.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
