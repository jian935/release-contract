# Built-in eval sets

Two suites: `dev.jsonl` and `holdout.jsonl`. Each line is one contract case
with a golden per-segment verdict and a `why` field explaining the expected
label.

**All cases are fabricated (编造).** There is no real launch data, no real
user traffic, no real model output, and no external annotation in this repo.
The demo contract is labelled `SYNTHETIC DEMO` in its `product` field so it
cannot be mistaken for a measured result.

## How the target set is defined

Cases are grouped by **structural kind** (which gate is exercised, how many
segments, whether traffic is fully declared), not by any keyword appearing in
the text. Defining a target set by "does the text contain this word" would
guarantee a perfect score and prove nothing. The nine kinds are:
`sample_gate`, `wilson_gate`, `harm_gate`, `fallback_gate`, `cost_gate`,
`coverage`, `clean_auto`, `combined`, `boundary`.

Both suites cover the same nine kinds but use different sample sizes,
thresholds, segment counts, ids and wording. The hold-out was written after
the engine was frozen; the rules were not tuned to it.

## Why it looks good

Both suites score 1.0000 on per-segment verdicts. **That is not evidence that
the tool works in production.** The golden labels were written by the author
of the rules, one branch per gate, so a deterministic implementation that
follows those rules must match them. What the score actually establishes is
narrow: the engine executes its declared rules consistently and can be
replayed offline, byte for byte.

The Wilson 95% intervals are wide (`[0.8928, 1.0]` for dev with 32 scored
segments, `[0.9011, 1.0]` for hold-out with 35). Even a perfect score on this
few items does not support a strong claim. Report the interval with the
accuracy, never the accuracy alone. Treat the table in the READMEs as a
**rule-consistency score**, not an effectiveness result.

If a future rules change causes the hold-out to drop, keep the lower number
and do not go back and tune the rules on it. If a golden label is simply
wrong, fix the label — not the engine.

## Checks that do not use golden labels

These exist because a golden label can only tell us whether the engine agrees
with its author.

- `python scripts/property_scan.py` — fixed-seed parameter scan asserting
  invariants: traffic accounting, byte-identical replay, Wilson
  monotonicity, ablation monotonicity, invalid-input rejection. A violation
  is a real bug, not a disagreeing label.
- `python scripts/blind_eval.py` — compares an independent annotator with
  the engine using the answer-free prompts in `blind/prompts.jsonl`. The
  protocol is in `blind/README.md`. **NOT RUN**: there is no measured
  agreement score, and none is claimed.

Both are invoked by `python scripts/quick_validate.py`.

## Reverse tests

A rule that nothing depends on is not a rule. `tests/test_engine.py` ablates
each of the 5 per-segment gates in turn and asserts that at least one eval
verdict changes. The 6th (global coverage) gate is tested differently: it
must report undeclared traffic without changing any verdict, and the traffic
accounting must still sum to full traffic.

## What is not scored

Evidence-risk flags (advisory Goodhart warnings) are not scored. Real-world
launch outcomes are not scored. Blind agreement is not scored because no
independent annotator has submitted labels. There is no measured number for
any of these, and none is claimed.

## Reproduce

```
python -m release_contract.cli eval
python eval/run_eval.py
python scripts/property_scan.py
python scripts/blind_eval.py
python scripts/quick_validate.py
```
