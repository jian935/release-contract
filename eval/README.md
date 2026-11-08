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
accuracy, never the accuracy alone.

If a future rules change causes the hold-out to drop, keep the lower number
and do not go back and tune the rules on it. If a golden label is simply
wrong, fix the label — not the engine.

## Reverse tests

A rule that nothing depends on is not a rule. `tests/test_engine.py` ablates
each of the 5 per-segment gates in turn and asserts that at least one eval
verdict changes. The 6th (global coverage) gate is tested differently: it
must report undeclared traffic without changing any verdict, and the traffic
accounting must still sum to full traffic.

## What is not scored

Evidence-risk flags (advisory Goodhart warnings) are not scored. Real-world
launch outcomes are not scored. There is no measured number for either, and
none is claimed.

## Reproduce

```
python -m release_contract.cli eval
python eval/run_eval.py
python scripts/quick_validate.py
```
