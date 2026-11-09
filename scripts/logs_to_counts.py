#!/usr/bin/env python3
"""Turn runtime logs into the counts CSV that `import` expects.

This is the only honest bridge from a running product to a release decision:
one JSON object per handled case, with a boolean outcome. Nothing is inferred —
a case without an outcome is counted as unlabelled and reported, never guessed.

Input (JSONL, one object per line):
    {"segment": "routine_faq", "ok": true}
    {"segment": "routine_faq", "ok": false}

Output: `id,n,successes` — exactly what `release-contract import` consumes.

Usage:
    python scripts/logs_to_counts.py run.jsonl -o counts.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path


class LogError(ValueError):
    """The log cannot be turned into counts without inventing something."""


def counts(text: str) -> tuple[list[dict], int]:
    """Return (rows, unlabelled) where unlabelled rows had no boolean `ok`."""
    seen: dict[str, list[int]] = {}
    unlabelled = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LogError("line %d is not JSON: %s" % (line_no, exc)) from None
        if not isinstance(record, dict):
            raise LogError("line %d is not an object" % line_no)
        segment = str(record.get("segment", "")).strip()
        if not segment:
            raise LogError("line %d has no segment" % line_no)
        ok = record.get("ok")
        bucket = seen.setdefault(segment, [0, 0])
        if ok is None:
            # A case with no outcome is not a success and not a failure; it is
            # excluded from n and reported, so the denominator stays honest.
            unlabelled += 1
            continue
        if not isinstance(ok, bool):
            raise LogError(
                "line %d: ok must be true/false, got %r" % (line_no, ok)
            )
        bucket[1] += 1
        if ok:
            bucket[0] += 1
    rows = [
        {"id": segment, "n": total, "successes": good}
        for segment, (good, total) in sorted(seen.items())
    ]
    return rows, unlabelled


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "n", "successes"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log", help="JSONL of {segment, ok}")
    ap.add_argument("-o", "--output", default="", help="write here instead of stdout")
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = ap.parse_args()

    try:
        rows, unlabelled = counts(Path(args.log).read_text(encoding="utf-8-sig"))
    except (OSError, LogError) as exc:
        print("invalid log: %s" % exc, file=sys.stderr)
        return 3
    if not rows:
        print("invalid log: no labelled cases found", file=sys.stderr)
        return 3

    payload = to_csv(rows)
    if args.output:
        target = Path(args.output)
        if target.exists() and not args.force:
            print("refusing to overwrite %s (pass --force)" % target, file=sys.stderr)
            return 3
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8", newline="\n")
        print("wrote %s" % target, file=sys.stderr)
    else:
        sys.stdout.write(payload)
    total = sum(r["n"] for r in rows)
    print(
        "counted %d cases over %d segments%s"
        % (
            total,
            len(rows),
            "; %d without an outcome were skipped, not guessed" % unlabelled
            if unlabelled
            else "",
        ),
        file=sys.stderr,
    )
    print(
        "next: python -m release_contract.cli import <this csv> --product \"...\"",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
