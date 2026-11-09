#!/usr/bin/env python3
"""Compare two blind rounds: inter-annotator agreement, not accuracy.

Round 1 has one reader. The only honest way to tell "the tool is conservative"
apart from "this reader was guessing" is a second independent reader on the same
cases. That comparison needs a number that is not just percent agreement,
because two readers who both default to `AUTO` would score high by accident.

Reported:
    - paired segments (only cases both rounds scored)
    - raw agreement
    - Cohen's kappa over AUTO / FENCE / HOLD
    - each round's agreement with the engine, on the same paired subset
    - the full list of reader-vs-reader disagreements

This is a measurement tool. It never publishes anything by itself.

Usage:
    python scripts/compare_rounds.py \
        eval/blind/rounds/round1/answers.csv \
        eval/blind/rounds/round2/answers.csv
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.engine import contract_from_dict, decide  # noqa: E402

PROMPTS = ROOT / "eval" / "blind" / "prompts.jsonl"
LABELS = ("AUTO", "FENCE", "HOLD")


def _blind_eval():
    spec = importlib.util.spec_from_file_location(
        "blind_eval", ROOT / "scripts" / "blind_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _flatten(path: Path) -> dict[tuple[str, str], str]:
    blind = _blind_eval()
    flat: dict[tuple[str, str], str] = {}
    for case in blind._load_annotations(path):
        for seg_id, verdict in case["verdicts"].items():
            flat[(case["id"], seg_id)] = verdict
    return flat


def _engine_verdicts() -> dict[tuple[str, str], str]:
    prompts = {
        p["id"]: p
        for p in (
            json.loads(line)
            for line in PROMPTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    out: dict[tuple[str, str], str] = {}
    for case_id, prompt in prompts.items():
        decision = decide(contract_from_dict(prompt["contract"]))
        for seg in decision.segments:
            out[(case_id, seg.id)] = seg.verdict
    return out


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Cohen's kappa for two raters over a fixed label set."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    expected = 0.0
    for label in LABELS:
        pa = sum(1 for a, _ in pairs if a == label) / n
        pb = sum(1 for _, b in pairs if b == label) / n
        expected += pa * pb
    if abs(1.0 - expected) < 1e-12:
        return None
    return (observed - expected) / (1.0 - expected)


def compare(path_a: Path, path_b: Path) -> dict[str, Any]:
    a = _flatten(path_a)
    b = _flatten(path_b)
    shared = sorted(set(a) & set(b))
    if not shared:
        raise ValueError("the two rounds share no scored segment")

    pairs = [(a[k], b[k]) for k in shared]
    engine = _engine_verdicts()
    agree = sum(1 for x, y in pairs if x == y)
    k = kappa(pairs)

    def _vs_engine(flat: dict[tuple[str, str], str]) -> dict[str, Any]:
        scored = [k_ for k_ in shared if k_ in flat and k_ in engine]
        if not scored:
            return {"segments": 0, "agree": 0, "rate": None}
        hit = sum(1 for k_ in scored if flat[k_] == engine[k_])
        return {
            "segments": len(scored),
            "agree": hit,
            "rate": round(hit / len(scored), 4),
        }

    disagreements = [
        {"case": k_[0], "segment": k_[1], "reader_a": a[k_], "reader_b": b[k_],
         "engine": engine.get(k_)}
        for k_ in shared
        if a[k_] != b[k_]
    ]
    counts = {label: {"a": 0, "b": 0} for label in LABELS}
    for x, y in pairs:
        counts[x]["a"] += 1
        counts[y]["b"] += 1

    return {
        "round_a": path_a.as_posix(),
        "round_b": path_b.as_posix(),
        "paired_segments": len(shared),
        "agreement": round(agree / len(shared), 4),
        "cohens_kappa": None if k is None else round(k, 4),
        "label_counts": counts,
        "a_vs_engine": _vs_engine(a),
        "b_vs_engine": _vs_engine(b),
        "disagreements": disagreements,
        "message": (
            "Inter-annotator agreement on the same cases. Kappa near 0 means the "
            "two readers share no more than chance on this label set; that would "
            "make the engine comparison uninformative rather than wrong."
        ),
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "rounds compared: %s vs %s" % (result["round_a"], result["round_b"]),
        "  paired segments   : %d" % result["paired_segments"],
        "  raw agreement     : %s" % result["agreement"],
        "  Cohen's kappa     : %s"
        % ("n/a (degenerate)" if result["cohens_kappa"] is None else result["cohens_kappa"]),
        "  reader A vs engine: %s over %d"
        % (result["a_vs_engine"]["rate"], result["a_vs_engine"]["segments"]),
        "  reader B vs engine: %s over %d"
        % (result["b_vs_engine"]["rate"], result["b_vs_engine"]["segments"]),
        "  reader-vs-reader disagreements: %d" % len(result["disagreements"]),
    ]
    for d in result["disagreements"]:
        lines.append(
            "    %s/%s A=%s B=%s engine=%s"
            % (d["case"], d["segment"], d["reader_a"], d["reader_b"], d["engine"])
        )
    lines.append("  " + result["message"])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("round_a", help="first filled sheet (CSV or JSONL)")
    ap.add_argument("round_b", help="second filled sheet (CSV or JSONL)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = compare(Path(args.round_a), Path(args.round_b))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
