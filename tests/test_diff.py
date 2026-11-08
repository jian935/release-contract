"""Property-check and diff unit tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from release_contract.diff import diff_contracts, diff_decisions
from release_contract.engine import Contract, Segment, contract_from_dict, decide, load_contract
from release_contract.properties import DEFAULT_SEED, scan

ROOT = Path(__file__).resolve().parents[1]
DEMO_V1 = ROOT / "examples" / "demo_contract.json"
DEMO_V2 = ROOT / "examples" / "demo_contract_v2.json"


class TestProperties(unittest.TestCase):
    def test_default_scan_finds_no_violations(self):
        result = scan()
        self.assertTrue(result["passed"], result["violations"])

    def test_fixed_seed_is_reproducible(self):
        a = scan(seed=DEFAULT_SEED, trials=40)
        b = scan(seed=DEFAULT_SEED, trials=40)
        self.assertTrue(a == b)

    def test_every_property_is_actually_checked(self):
        result = scan(trials=10)
        self.assertTrue(all(n > 0 for n in result["checked"].values()))

    def test_property_scan_does_not_read_golden_labels(self):
        """The scan must work even with the eval suites unavailable."""
        from release_contract import properties

        self.assertTrue(callable(properties.scan))
        result = properties.scan(trials=5)
        self.assertTrue("violations" in result)


class TestDiff(unittest.TestCase):
    def test_demo_versions_show_both_directions(self):
        result = diff_contracts(load_contract(DEMO_V1), load_contract(DEMO_V2))
        changes = {r["change"] for r in result["segments"]}
        self.assertTrue("regression" in changes)
        self.assertTrue("improvement" in changes)

    def test_identical_contracts_have_no_regressions(self):
        c = load_contract(DEMO_V1)
        result = diff_decisions(decide(c), decide(c))
        self.assertTrue(all(r["change"] == "unchanged" for r in result["segments"]))
        self.assertTrue(result["summary"]["regression"] == 0)

    def test_traffic_delta_matches_before_after(self):
        result = diff_contracts(load_contract(DEMO_V1), load_contract(DEMO_V2))
        for key, delta in result["traffic_delta"].items():
            self.assertTrue(
                abs(delta - (result["traffic_after"][key] - result["traffic_before"][key])) < 1e-6
            )

    def test_added_and_removed_segments_are_reported(self):
        def one(ids):
            return Contract(
                product="p",
                segments=tuple(
                    Segment(
                        id=i, volume_share=0.5, n=250, successes=240,
                        harm_if_wrong="low", fallback="none",
                        cost_per_case=0.02, human_review_cost=0.0,
                    )
                    for i in ids
                ),
            )

        result = diff_contracts(one(("a", "b")), one(("b", "c")))
        kinds = {(r["id"], r["change"]) for r in result["segments"]}
        self.assertTrue(("a", "removed") in kinds)
        self.assertTrue(("c", "added") in kinds)
        self.assertTrue(("b", "unchanged") in kinds)


class TestFailOnContract(unittest.TestCase):
    def test_strict_loader_rejects_unknown_gate_key(self):
        with self.assertRaises(Exception):
            contract_from_dict(
                {"product": "p", "segments": [], "guardrails": {"unknown_gate": 1}}
            )


if __name__ == "__main__":
    unittest.main()
