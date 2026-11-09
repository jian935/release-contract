"""Inter-annotator agreement must not be reported as raw percent alone.

Two readers who both default to AUTO would agree 100% by accident; kappa is the
number that says whether they share a rule or a habit.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "compare_rounds", ROOT / "scripts" / "compare_rounds.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestKappa(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_perfect_agreement_is_one(self):
        self.assertTrue(self.mod.kappa([("AUTO", "AUTO"), ("FENCE", "FENCE")]) == 1.0)

    def test_chance_agreement_is_zero(self):
        # A says AUTO twice; B splits one AUTO one FENCE. po=0.5, pe=0.5.
        self.assertTrue(abs(self.mod.kappa([("AUTO", "AUTO"), ("AUTO", "FENCE")])) < 1e-12)

    def test_degenerate_case_returns_none_instead_of_dividing_by_zero(self):
        self.assertTrue(self.mod.kappa([("AUTO", "AUTO")]) is None)


class TestCompare(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def _write(self, name: str, rows: list[tuple[str, str, str]]) -> Path:
        tmp = tempfile.TemporaryDirectory(dir=str(ROOT))
        path = Path(tmp.name) / name
        body = "题目编号,分片名,你的判定\n" + "".join(
            "%s,%s,%s\n" % r for r in rows
        )
        path.write_text(body, encoding="utf-8-sig")
        self.addCleanup(tmp.cleanup)
        return path

    def test_pairs_only_the_shared_segments(self):
        a = self._write("a.csv", [("dev-001", "thin", "HOLD")])
        b = self._write(
            "b.csv", [("dev-001", "thin", "HOLD"), ("dev-002", "almost", "AUTO")]
        )
        result = self.mod.compare(a, b)
        self.assertTrue(result["paired_segments"] == 1)
        self.assertTrue(result["agreement"] == 1.0)
        self.assertTrue(result["disagreements"] == [])

    def test_reports_reader_disagreements_with_both_labels(self):
        a = self._write("a.csv", [("dev-004", "point_ok", "AUTO")])
        b = self._write("b.csv", [("dev-004", "point_ok", "FENCE")])
        result = self.mod.compare(a, b)
        self.assertTrue(len(result["disagreements"]) == 1)
        d = result["disagreements"][0]
        self.assertTrue(d["reader_a"] == "AUTO" and d["reader_b"] == "FENCE")
        self.assertTrue(d["engine"] == "FENCE")

    def test_no_shared_segment_is_an_error(self):
        a = self._write("a.csv", [("dev-001", "thin", "HOLD")])
        b = self._write("b.csv", [("dev-002", "almost", "HOLD")])
        with self.assertRaises(ValueError):
            self.mod.compare(a, b)


if __name__ == "__main__":
    unittest.main()
