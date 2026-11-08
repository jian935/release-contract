"""Project-level locks. The single source of truth is release_contract.selfcheck."""

from __future__ import annotations

import unittest

from release_contract.selfcheck import run_checks


class TestProjectLocks(unittest.TestCase):
    def test_every_self_check_passes(self):
        failed = ["%s (%s)" % (c.name, c.detail) for c in run_checks() if not c.ok]
        self.assertTrue(not failed, "failing self-checks: %s" % failed)

    def test_self_check_list_is_not_empty(self):
        self.assertTrue(len(run_checks()) > 0)

    def test_all_green_is_not_treated_as_no_gaps(self):
        """Guard the guard: the report must keep the unmeasured disclaimer."""
        from release_contract.selfcheck import render

        text = render(run_checks())
        self.assertTrue("all-green is not proof of no gaps" in text)


if __name__ == "__main__":
    unittest.main()
