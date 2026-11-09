"""The what-if script must model exactly the two scenarios it claims to.

Its numbers go into `DESIGN.md`, so the cheap failure mode to guard against is a
script that quietly widens one scenario and inflates the cost of a decision.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "whatif_rules", ROOT / "scripts" / "whatif_rules.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestWhatIfScenarios(unittest.TestCase):
    def setUp(self):
        self.mod = _load()
        self.result = self.mod.run()

    def test_every_segment_is_counted(self):
        self.assertTrue(self.result["segments"] > 0)
        self.assertTrue(len(self.result["flip_a"]) <= self.result["segments"])
        self.assertTrue(len(self.result["flip_b"]) <= self.result["segments"])

    def test_scenario_a_only_loosens(self):
        for row in self.result["flip_a"]:
            self.assertTrue(row["current"] == "FENCE")
            self.assertTrue(row["scenario_a"] == "AUTO")

    def test_scenario_b_only_escalates(self):
        for row in self.result["flip_b"]:
            self.assertTrue(row["current"] == "HOLD")
            self.assertTrue(row["scenario_b"] == "FENCE")

    def test_scenarios_never_claim_a_change_that_did_not_happen(self):
        for row in self.result["flip_a"] + self.result["flip_b"]:
            self.assertTrue(row["scenario_a"] in (None, "AUTO"))
            self.assertTrue(row["scenario_b"] in (None, "FENCE"))

    def test_render_states_that_nothing_is_implemented(self):
        text = self.mod.render(self.result)
        self.assertTrue("Neither scenario is implemented" in text)
        self.assertTrue("of %d segments" % self.result["segments"] in text)


if __name__ == "__main__":
    unittest.main()
