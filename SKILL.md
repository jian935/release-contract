---
name: release-contract
description: >-
  Decide which traffic segments of an AI/LLM product the existing offline
  evidence is strong enough to release to. Use when a PM must answer "can we
  ship to all users, which segments need human fallback, and what triggers a
  rollback?" Builds a deterministic, auditable per-segment go/no-go contract
  from raw eval counts (successes and n, never a chosen rate). Not a code
  deployment audit, not an eval framework, and not a model-quality scorer.
---

# release-contract

A release contract turns one offline eval result into a **per-segment launch
decision**. It answers three questions a PM actually has to sign off on:

1. Which traffic can be automated (`AUTO`)?
2. Which must be fenced to a human or disabled (`FENCE`), and which merely
   lacks enough evidence (`HOLD`)?
3. What observed condition forces a rollback?

## When to use

- A model / prompt / agent version is about to go live and evidence differs
  by user segment.
- Someone proposes "ship to 60% of traffic" and you need to know what the
  other 40% is.
- A post-incident review asks which segment should have been fenced.
- A new model version needs a segment-by-segment comparison against the
  previous one (`diff`).

## When NOT to use

- To run evals or compute quality scores. Use promptfoo, Langfuse, DeepEval,
  or your own harness; this skill consumes their raw counts.
- To audit code, CI, secrets or deployment readiness. `ship-gate` style tools
  do that; this one audits **evidence coverage**, not the codebase.
- To decide with a vibe. Every verdict here comes from a named gate.

## Input

A JSON contract (`examples/demo_contract.json`) with `product`,
`guardrails`, and `segments`. Each segment declares:

`id`, `volume_share`, `n`, `successes`, `harm_if_wrong`, `fallback`,
`cost_per_case`, `human_review_cost`.

Raw counts are mandatory: a caller cannot supply a flattering rate with a
self-chosen denominator. Declared `volume_share` may sum to at most 1.0;
anything missing is reported as `uncovered`, never dropped.

## Commands

```
python -m release_contract.cli decide examples/demo_contract.json
python -m release_contract.cli decide examples/demo_contract.json --json
python -m release_contract.cli gates
python -m release_contract.cli eval
python -m release_contract.cli version
python -m release_contract.cli diff examples/demo_contract.json examples/demo_contract_v2.json
python scripts/property_scan.py
python scripts/blind_eval.py
```

`decide --fail-on FENCE,HOLD` returns a non-zero exit code when any segment
hits a listed verdict, so a pipeline can gate on it.

## The 6 gates

| gate | effect |
|---|---|
| G1_SAMPLE | `n` below `min_sample_size` → `HOLD` (missing evidence, not a failure) |
| G2_WILSON | Wilson lower bound below `min_success_rate` → `FENCE` |
| G3_HARM | `harm_if_wrong` above `max_harm` → `FENCE`, regardless of accuracy |
| G4_FALLBACK | high-harm segment with `fallback=none` → `FENCE` |
| G5_COST | loaded cost including human fallback above budget → `FENCE` |
| G6_COVERAGE | global: undeclared traffic is reported, never hidden |

Strictness is `HOLD > FENCE > AUTO`. Every triggered gate is printed with its
reason, so a `NO-GO` can be argued with instead of just accepted.

`G2` is the important one. At `n=30, successes=30` the observed rate is
1.000 but the Wilson lower bound is 0.8865, below a 0.9 bar: zero observed
failures is not proof. Two segments with the same 0.970 point estimate can
get opposite verdicts purely because their interval widths differ.

## Output

Per-segment verdicts, four traffic buckets that always sum to full traffic
(`auto` / `fence` / `hold` / `uncovered`), advisory evidence-risk flags, and
a concrete rollback trigger per `AUTO` segment. JSON output is stable-key and
suitable for a CI golden diff. `diff` reports, per segment, whether a version
change is a regression, an improvement, or unchanged, plus the traffic delta.

Evidence-risk flags (`uncovered_traffic`, `threshold_hugging`,
`no_failure_observed`, `uniform_sample_sizes`, `zero_cost`) are advisory.
They never change a verdict — otherwise the tool could be tuned to look good.

## Boundaries (read before citing any number)

- The engine calls no LLM, no network and no randomness. Same JSON in,
  byte-identical decision out; this is required for offline reproducibility.
- The two bundled eval sets are **fabricated**, written by the rule author.
  Their perfect scores are a rule-consistency check, not real-world
  effectiveness. See `eval/README.md`.
- A blind protocol and answer-free prompts exist in `eval/blind/`. One local
  round was returned, but **no agreement score is published**: the filled
  sheet is not in the repository, so the number would be unverifiable. The
  round's repeatable finding: every disagreement was the Wilson gate (point
  estimate above the floor, lower bound below it), never a release the
  annotator would have blocked. Rank it as a conservative bias, not accuracy.
- `scripts/property_scan.py` checks invariants over a fixed-seed parameter
  space without using any golden label. It can find bugs; it cannot validate
  whether the gates reflect good product judgement.
- No real launch data, no real users, no external annotation, and no measured
  accuracy for evidence-risk flags or real outcomes exist in this project.
- The tool does not tell you whether your eval was well designed. A curated
  test set that hides messy edge cases will still produce green verdicts;
  that is exactly what the Goodhart flags are meant to surface.
- Upstream, `complaint-to-eval` answers "what should we test"; this skill
  answers "can we ship". They are complementary and neither replaces the
  other.

Author: jian935 · MIT
