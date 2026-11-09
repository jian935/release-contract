"""The demo must call the interpreter it is running under, never bare `python`.

On Windows a launcher stub can shadow `python`, exit 0 and print nothing. That
produced a screen recording of four commands with no output at all. The failure
is silent, so it needs a test rather than a comment.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_demo():
    spec = importlib.util.spec_from_file_location(
        "demo_script", ROOT / "scripts" / "demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDemoUsesTheRunningInterpreter(unittest.TestCase):
    def setUp(self):
        self.demo = _load_demo()

    def test_no_step_invokes_a_bare_python(self):
        for template, _note, _show in self.demo.STEPS:
            first = template.strip().split()[0]
            self.assertTrue(
                first == "{py}",
                "step must start with {py}, found %r" % first,
            )
            self.assertTrue(" python " not in " %s " % template)

    def test_expanded_command_points_at_this_interpreter(self):
        for template, _note, _show in self.demo.STEPS:
            expanded = self.demo.expand(template)
            self.assertTrue(sys.executable in expanded)
            self.assertTrue("{py}" not in expanded)

    def test_display_alias_only_shortens_the_path(self):
        template = self.demo.STEPS[0][0]
        shown = self.demo.for_display(self.demo.expand(template))
        self.assertTrue(shown.startswith("python -m release_contract.cli"))
        # The rest of the command is untouched.
        self.assertTrue(shown.endswith(template.split("{py}", 1)[1]))

    def test_every_step_carries_a_boolean_output_switch(self):
        for _template, _note, show in self.demo.STEPS:
            self.assertIsInstance(show, bool)


if __name__ == "__main__":
    unittest.main()
