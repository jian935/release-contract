"""The published round must be regenerable, and must not be silently replaced.

These tests guard the mechanism, not the number: if the engine or the intake
changes, `result.json` must be regenerated deliberately, not drift quietly.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "eval" / "blind" / "rounds" / "round1" / "answers.csv"
FROZEN = ROOT / "eval" / "blind" / "rounds" / "round1" / "result.json"


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPublishRound(unittest.TestCase):
    def setUp(self):
        self.mod = _load("publish_round", "scripts/publish_round.py")

    def test_published_result_matches_a_fresh_build(self):
        import json

        frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
        fresh = self.mod.build(
            SHEET,
            frozen["round"],
            frozen["date"],
            frozen["annotator"],
        )
        for key in ("agreement", "wilson95_ci", "scored_segments", "correct"):
            self.assertTrue(fresh[key] == frozen[key])
        self.assertTrue(fresh["disagreements"] == frozen["disagreements"])
        self.assertTrue(fresh["disagreement_causes"] == frozen["disagreement_causes"])

    def test_build_is_deterministic(self):
        first = self.mod.build(SHEET, 1, "2026-11-09", "x")
        second = self.mod.build(SHEET, 1, "2026-11-09", "x")
        self.assertTrue(first == second)

    def test_result_records_which_prompt_set_it_was_scored_against(self):
        # The model cross-check uses the second batch. Without this field the
        # self-check would recompute it against the first batch and reject
        # every nb-* row.
        batch = ROOT / "eval" / "blind" / "next_batch" / "prompts.jsonl"
        sheet = ROOT / "eval" / "blind" / "model_check" / "answers.csv"
        fresh = self.mod.build(
            sheet, 4, "2026-11-09", "a model", batch, "model_check"
        )
        self.assertTrue(fresh["prompts"] == "eval/blind/next_batch/prompts.jsonl")
        self.assertTrue(fresh["kind"] == "model_check")
        # The default must stay the first batch so no older call site silently
        # starts scoring against a different question set.
        default = self.mod.build(SHEET, 1, "2026-11-09", "x")
        self.assertTrue(default["prompts"] == "eval/blind/prompts.jsonl")
        self.assertTrue(default["kind"] == "blind_round")

    def test_refuses_to_overwrite_a_different_published_result(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            out = Path(tmp) / "result.json"
            out.write_text('{"agreement": 0.9999}\n', encoding="utf-8")
            argv = sys.argv
            sys.argv = [
                "publish_round.py",
                "--round", "1",
                "--sheet", str(SHEET),
                "--out", str(out),
                "--date", "2026-11-09",
                "--annotator", "x",
            ]
            try:
                code = self.mod.main()
            finally:
                sys.argv = argv
            self.assertTrue(code == 2)
            self.assertTrue("0.9999" in out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
