"""The README animation is rendered from real stdout, not screenshotted.

The image itself needs Pillow to regenerate, which not every CI interpreter has.
So the check that survives everywhere is a hash sidecar: it records the SHA-256
of the text the GIF was built from, and any engine change breaks it until the
image is re-rendered.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIF = ROOT / "assets" / "demo.gif"
SIDECAR = ROOT / "assets" / "demo.gif.json"

from release_contract.engine import decide, load_contract  # noqa: E402
from release_contract.report import render_text  # noqa: E402


def _live_hash() -> str:
    text = render_text(decide(load_contract(ROOT / "examples" / "demo_contract.json")))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestDemoAsset(unittest.TestCase):
    def test_sidecar_matches_current_output(self):
        meta = json.loads(SIDECAR.read_text(encoding="utf-8"))
        self.assertTrue(meta["source_sha256"] == _live_hash())

    def test_gif_is_a_real_gif(self):
        data = GIF.read_bytes()
        self.assertTrue(data[:6] in (b"GIF89a", b"GIF87a"))
        self.assertTrue(len(data) > 20_000)

    def test_sidecar_declares_it_is_not_a_capture(self):
        meta = json.loads(SIDECAR.read_text(encoding="utf-8"))
        self.assertTrue("not a screen capture" in meta["note"].lower())

    def test_renderer_exists(self):
        self.assertTrue((ROOT / "scripts" / "render_demo_gif.py").exists())


class TestRenderer(unittest.TestCase):
    def setUp(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")

    def test_render_is_deterministic_and_carries_the_hash(self):
        spec = importlib.util.spec_from_file_location(
            "render_demo_gif", ROOT / "scripts" / "render_demo_gif.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        first, meta_a = module.build()
        second, meta_b = module.build()
        self.assertTrue(first == second)
        self.assertTrue(meta_a["source_sha256"] == _live_hash())
        self.assertTrue(meta_a["source_sha256"] == meta_b["source_sha256"])


if __name__ == "__main__":
    unittest.main()
