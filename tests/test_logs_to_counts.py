"""Runtime logs -> counts CSV. The denominator must stay honest.

A case with no outcome is not a success and not a failure: it is excluded from
`n` and reported. Anything else would let a logging gap look like accuracy.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "logs_to_counts", ROOT / "scripts" / "logs_to_counts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCounts(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_counts_per_segment(self):
        rows, unlabelled = self.mod.counts(
            '{"segment":"a","ok":true}\n'
            '{"segment":"a","ok":false}\n'
            '{"segment":"a","ok":true}\n'
        )
        self.assertTrue(rows == [{"id": "a", "n": 3, "successes": 2}])
        self.assertTrue(unlabelled == 0)

    def test_missing_outcome_is_excluded_not_counted_as_failure(self):
        rows, unlabelled = self.mod.counts(
            '{"segment":"a","ok":true}\n{"segment":"a"}\n'
        )
        self.assertTrue(rows == [{"id": "a", "n": 1, "successes": 1}])
        self.assertTrue(unlabelled == 1)

    def test_blank_lines_are_ignored(self):
        rows, _ = self.mod.counts('{"segment":"a","ok":true}\n\n')
        self.assertTrue(len(rows) == 1)

    def test_non_boolean_outcome_is_rejected(self):
        with self.assertRaises(self.mod.LogError):
            self.mod.counts('{"segment":"a","ok":"yes"}\n')

    def test_missing_segment_is_rejected(self):
        with self.assertRaises(self.mod.LogError):
            self.mod.counts('{"ok":true}\n')

    def test_malformed_line_names_the_line(self):
        with self.assertRaises(self.mod.LogError) as ctx:
            self.mod.counts('{"segment":"a","ok":true}\nnot json\n')
        self.assertTrue("line 2" in str(ctx.exception))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        import sys

        old = sys.argv
        sys.argv = ["logs_to_counts.py"] + argv
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = self.mod.main()
        finally:
            sys.argv = old
        return code, out.getvalue(), err.getvalue()

    def test_writes_csv_and_names_the_next_command(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            log = Path(tmp) / "run.jsonl"
            log.write_text('{"segment":"a","ok":true}\n', encoding="utf-8")
            csv = Path(tmp) / "counts.csv"
            code, _, err = self._run([str(log), "-o", str(csv)])
            self.assertTrue(code == 0)
            self.assertTrue(csv.exists())
            self.assertTrue("release_contract.cli import" in err)
            self.assertTrue("id,n,successes" in csv.read_text(encoding="utf-8"))

    def test_empty_log_is_an_input_error(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            log = Path(tmp) / "empty.jsonl"
            log.write_text("\n", encoding="utf-8")
            code, _, err = self._run([str(log)])
            self.assertTrue(code == 3)
            self.assertTrue("no labelled cases" in err)


if __name__ == "__main__":
    unittest.main()
