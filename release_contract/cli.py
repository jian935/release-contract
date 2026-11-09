"""Command line interface. Zero third-party dependencies.

Exit codes (stable, documented in README and SKILL.md):
    0  success
    2  a segment hit a verdict listed in --fail-on (pipeline gate)
    3  invalid input: unreadable file, malformed JSON, or contract rejected
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .diff import diff_contracts, render as render_diff
from .engine import ALL_GATES, ContractError, decide, load_contract
from .evalset import render as render_eval
from .evalset import run_suite
from .report import render_text, to_json

COMMANDS: tuple[str, ...] = ("decide", "diff", "validate", "init", "gates", "eval", "version")

EXIT_OK = 0
EXIT_GATE = 2
EXIT_INPUT = 3

GATE_DOCS: tuple[tuple[str, str], ...] = (
    ("G1_SAMPLE", "n below min_sample_size -> HOLD (missing evidence, not a failure)"),
    ("G2_WILSON", "Wilson lower bound below min_success_rate -> FENCE"),
    ("G3_HARM", "harm_if_wrong above max_harm -> FENCE regardless of accuracy"),
    ("G4_FALLBACK", "high-harm segment with fallback=none -> FENCE"),
    ("G5_COST", "loaded cost incl. human fallback above max_cost_per_case -> FENCE"),
    ("G6_COVERAGE", "global: undeclared traffic is reported, never dropped"),
)

# The template produces HOLD on purpose: it must never look shippable before a
# single real count has been entered.
TEMPLATE = {
    "product": "CHANGE ME: what you are releasing, and which version",
    "guardrails": {
        "min_sample_size": 100,
        "min_success_rate": 0.9,
        "max_harm": "medium",
        "max_cost_per_case": 0.5,
        "z": 1.96,
    },
    "segments": [
        {
            "id": "CHANGE_ME_segment",
            "volume_share": 1.0,
            "n": 0,
            "successes": 0,
            "harm_if_wrong": "low",
            "fallback": "none",
            "cost_per_case": 0.0,
            "human_review_cost": 0.0,
        }
    ],
}


def _cmd_decide(args: argparse.Namespace) -> int:
    decision = decide(load_contract(args.contract))
    print(to_json(decision) if args.json else render_text(decision))
    if args.fail_on:
        wanted = {v.strip().upper() for v in args.fail_on.split(",") if v.strip()}
        unknown = wanted - {"AUTO", "FENCE", "HOLD"}
        if unknown:
            print(
                "--fail-on accepts AUTO/FENCE/HOLD only; unknown: %s" % sorted(unknown),
                file=sys.stderr,
            )
            return EXIT_INPUT
        if any(s.verdict in wanted for s in decision.segments):
            return EXIT_GATE
    return EXIT_OK


def _cmd_validate(args: argparse.Namespace) -> int:
    contract = load_contract(args.contract)
    declared = sum(s.volume_share for s in contract.segments)
    summary = {
        "product": contract.product,
        "segments": len(contract.segments),
        "declared_share": round(declared, 6),
        "uncovered_share": round(max(0.0, 1.0 - declared), 6),
        "guardrails": {
            "min_sample_size": contract.guardrails.min_sample_size,
            "min_success_rate": contract.guardrails.min_success_rate,
            "max_harm": contract.guardrails.max_harm,
            "max_cost_per_case": contract.guardrails.max_cost_per_case,
            "z": contract.guardrails.z,
        },
        "valid": True,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("contract is valid")
        print("  product        : %s" % summary["product"])
        print("  segments       : %d" % summary["segments"])
        print("  declared share : %.6f" % summary["declared_share"])
        print(
            "  uncovered      : %.6f%s"
            % (
                summary["uncovered_share"],
                "  (reported, never dropped)" if summary["uncovered_share"] > 0 else "",
            )
        )
    return EXIT_OK


def _cmd_init(args: argparse.Namespace) -> int:
    text = json.dumps(TEMPLATE, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        if path.exists() and not args.force:
            print(
                "refusing to overwrite %s (pass --force)" % path, file=sys.stderr
            )
            return EXIT_INPUT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        print("wrote %s" % path)
        print("Next: replace the n / successes placeholders with real counts,")
        print("      then run: python -m release_contract.cli decide %s" % path)
    else:
        sys.stdout.write(text)
        print(
            "# template has n=0 -> HOLD by design; enter real counts before shipping",
            file=sys.stderr,
        )
    return EXIT_OK


def _cmd_gates(_args: argparse.Namespace) -> int:
    print("release-contract gates (%d, all deterministic):" % len(ALL_GATES))
    for name, doc in GATE_DOCS:
        print("  %-14s %s" % (name, doc))
    print("")
    print("Verdicts: AUTO (release to this segment) / FENCE (human or disabled) / HOLD (evidence missing)")
    print("Strictness: HOLD > FENCE > AUTO. Every triggered gate is listed.")
    return EXIT_OK


def _cmd_eval(_args: argparse.Namespace) -> int:
    for which in ("dev", "holdout"):
        print(render_eval(run_suite(which)))
        print("")
    print("These sets are synthetic and written by the rule author. See eval/README.md.")
    return EXIT_OK


def _cmd_diff(args: argparse.Namespace) -> int:
    result = diff_contracts(load_contract(args.old), load_contract(args.new))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_diff(result))
    if args.fail_on_regression and result["summary"]["regression"]:
        return EXIT_GATE
    return EXIT_OK


def _cmd_version(_args: argparse.Namespace) -> int:
    print("release-contract %s" % __version__)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release-contract",
        description="Deterministic, auditable release gates for AI products.",
    )
    parser.add_argument("--version", action="version", version="release-contract %s" % __version__)
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

    p_validate = sub.add_parser(
        "validate", help="check a contract without deciding it (exit 3 when invalid)"
    )
    p_validate.add_argument("contract", help="path to contract JSON")
    p_validate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p_validate.set_defaults(func=_cmd_validate)

    p_init = sub.add_parser("init", help="print or write a valid starter contract")
    p_init.add_argument("-o", "--output", default="", help="write to this path instead of stdout")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing file")
    p_init.set_defaults(func=_cmd_init)

    sub.add_parser("gates", help="list the six gates").set_defaults(func=_cmd_gates)
    sub.add_parser("eval", help="run the built-in dev and hold-out sets").set_defaults(func=_cmd_eval)
    sub.add_parser("version", help="print version").set_defaults(func=_cmd_version)

    p_diff = sub.add_parser("diff", help="compare two contract versions")
    p_diff.add_argument("old", help="path to the earlier contract JSON")
    p_diff.add_argument("new", help="path to the later contract JSON")
    p_diff.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p_diff.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="exit 2 when any segment got worse",
    )
    p_diff.set_defaults(func=_cmd_diff)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ContractError as exc:
        print("invalid contract: %s" % exc, file=sys.stderr)
        return EXIT_INPUT
    except json.JSONDecodeError as exc:
        print("invalid JSON: %s" % exc, file=sys.stderr)
        return EXIT_INPUT
    except OSError as exc:
        print("cannot read input: %s" % exc, file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    sys.exit(main())
