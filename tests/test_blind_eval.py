"""Plumbing tests for the blind-evaluation CSV intake. NOT a measurement.

The verdicts written below are deliberately arbitrary. They only verify that
the script reads a filled CSV, skips undecided rows, rejects invalid labels and
reports disagreements. No number produced here may be quoted as a
blind-evaluation result.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "blind_eval", ROOT / "scripts" / "blind_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBlindIntake(unittest.TestCase):
    def setUp(self):
        self.mod = _load_module()

    def _csv(self, text: str):
        tmp = tempfile.TemporaryDirectory(dir=str(ROOT))
        path = Path(tmp.name) / "answer_sheet.csv"
        path.write_text(text, encoding="utf-8")
        return tmp, path

    def test_missing_file_reports_not_run(self):
        result = self.mod.run(ROOT / "eval" / "blind" / "no_such_file.csv")
        self.assertTrue(result["status"] == "no_annotations")
        self.assertTrue(result["agreement"] is None)

    def test_csv_intake_skips_undecided_rows(self):
        tmp, path = self._csv(
            "id,segment_id,verdict,rationale\n"
            "dev-001,thin,AUTO,arbitrary test value\n"
            "dev-002,almost,,\n"
        )
        with tmp:
            result = self.mod.run(path)
        self.assertTrue(result["status"] == "measured")
        self.assertTrue(result["scored_segments"] == 1)
        self.assertTrue(result["unannotated_segments"] > 0)
        self.assertTrue(result["disagreements"])

    def test_all_blank_reports_no_score(self):
        tmp, path = self._csv(
            "id,segment_id,verdict,rationale\ndev-001,thin,,\n"
        )
        with tmp:
            result = self.mod.run(path)
        self.assertTrue(result["status"] == "no_annotations")
        self.assertTrue(result["agreement"] is None)

    def test_invalid_verdict_is_rejected(self):
        tmp, path = self._csv(
            "id,segment_id,verdict,rationale\ndev-001,thin,MAYBE,,\n"
        )
        with tmp:
            with self.assertRaises(ValueError):
                self.mod.run(path)

    def test_single_sheet_chinese_columns_are_accepted(self):
        tmp, path = self._csv(
            "题目编号,分片名,你的判定,理由\n"
            "dev-001,thin,AUTO,one-sheet plumbing test\n"
        )
        with tmp:
            result = self.mod.run(path)
        self.assertTrue(result["status"] == "measured")
        self.assertTrue(result["scored_segments"] == 1)

    def test_render_of_not_run_never_invents_a_number(self):
        result = self.mod.run(ROOT / "eval" / "blind" / "no_such_file.csv")
        text = self.mod.render(result)
        self.assertTrue("NOT RUN" in text)


if __name__ == "__main__":
    unittest.main()
