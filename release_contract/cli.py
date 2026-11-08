"""Command line interface. Zero third-party dependencies."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .diff import diff_contracts, render as render_diff
from .engine import ALL_GATES, decide, load_contract
from .evalset import render as render_eval
from .evalset import run_suite
from .report import render_text, to_json

COMMANDS: tuple[str, ...] = ("decide", "gates", "eval", "version", "diff")

GATE_DOCS: tuple[tuple[str, str], ...] = (
    ("G1_SAMPLE", "n below min_sample_size -> HOLD (missing evidence, not a failure)"),
    ("G2_WILSON", "Wilson lower bound below min_success_rate -> FENCE"),
    ("G3_HARM", "harm_if_wrong above max_harm -> FENCE regardless of accuracy"),
    ("G4_FALLBACK", "high-harm segment with fallback=none -> FENCE"),
    ("G5_COST", "loaded cost incl. human fallback above max_cost_per_case -> FENCE"),
    ("G6_COVERAGE", "global: undeclared traffic is reported, never dropped"),
)


def _cmd_decide(args: argparse.Namespace) -> int:
    decision = decide(load_contract(args.contract))
    print(to_json(decision) if args.json else render_text(decision))
    if args.fail_on:
        wanted = {v.strip().upper() for v in args.fail_on.split(",") if v.strip()}
        if any(s.verdict in wanted for s in decision.segments):
            return 2
    return 0


def _cmd_gates(_args: argparse.Namespace) -> int:
    print("release-contract gates (%d, all deterministic):" % len(ALL_GATES))
    for name, doc in GATE_DOCS:
        print("  %-14s %s" % (name, doc))
    print("")
    print("Verdicts: AUTO (release to this segment) / FENCE (human or disabled) / HOLD (evidence missing)")
    print("Strictness: HOLD > FENCE > AUTO. Every triggered gate is listed.")
    return 0


def _cmd_eval(_args: argparse.Namespace) -> int:
    for which in ("dev", "holdout"):
        print(render_eval(run_suite(which)))
        print("")
    print("These sets are synthetic and written by the rule author. See eval/README.md.")
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    result = diff_contracts(load_contract(args.old), load_contract(args.new))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_diff(result))
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    print("release-contract %s" % __version__)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release-contract",
        description="Deterministic, auditable release gates for AI products.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_decide = sub.add_parser("decide", help="decide a contract JSON file")
    p_decide.add_argument("contract", help="path to contract JSON")
    p_decide.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p_decide.add_argument(
        "--fail-on",
        default="",
        help="comma-separated verdicts (AUTO/FENCE/HOLD) that produce exit code 2",
    )
    p_decide.set_defaults(func=_cmd_decide)

    sub.add_parser("gates", help="list the six gates").set_defaults(func=_cmd_gates)
    sub.add_parser("eval", help="run the built-in dev and hold-out sets").set_defaults(func=_cmd_eval)
    sub.add_parser("version", help="print version").set_defaults(func=_cmd_version)

    p_diff = sub.add_parser("diff", help="compare two contract versions")
    p_diff.add_argument("old", help="path to the earlier contract JSON")
    p_diff.add_argument("new", help="path to the later contract JSON")
    p_diff.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p_diff.set_defaults(func=_cmd_diff)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
