---
name: release-contract
description: >-
  Decide which traffic segments of an AI/LLM product the existing offline
  evidence is strong enough to release to. Use when someone asks "can we ship
  to all users, which segments need human fallback, and what forces a
  rollback?" Turns raw eval counts (successes and n — never a chosen rate)
  into a deterministic per-segment go/no-go contract with four traffic buckets
  that always sum to full traffic. Not a code deployment audit, not an eval
  runner, not a model-quality scorer.
---

# release-contract

One offline eval result → one **per-segment launch decision**. It answers the
three questions a PM has to sign personally:

1. Which traffic can be automated (`AUTO`)?
2. Which must be fenced to a human or disabled (`FENCE`), and which merely
   lacks evidence (`HOLD`)?
3. What observed condition forces a rollback?

## When to use

- A model / prompt / agent version is about to ship and evidence differs by
  user segment.
- Someone proposes "ship to 60% of traffic" and you must say what the other
  40% is.
- A post-incident review asks which segment should have been fenced.
- A new version needs a segment-by-segment comparison against the old one.

## When NOT to use

- To run evals or score quality. Use promptfoo, Langfuse, DeepEval or your own
  harness; this skill consumes their raw counts.
- To audit code, CI, secrets or deployment readiness — that is `ship-gate`
  territory. This audits **evidence coverage**, not the codebase.
- To decide from a vibe. Every verdict comes from a named gate.

## Workflow (do these four steps in order)

```bash
# 1. start from a valid template; it decides HOLD until real counts exist
python -m release_contract.cli init -o contract.json

# 2. replace n / successes / costs with real eval counts, then check the shape
python -m release_contract.cli validate contract.json

# 3. decide
python -m release_contract.cli decide contract.json --json > decision.json

# 4. gate a pipeline on it (exit 2 when a listed verdict appears)
python -m release_contract.cli decide contract.json --fail-on FENCE,HOLD
```

Never invent counts. If a segment has no evidence, leave `n` small and let
`G1` return `HOLD`; `HOLD` is an honest answer, `AUTO` on thin evidence is not.

Coming straight from an eval run? `import` turns a CSV of counts into a
contract without hand-typing JSON:

```bash
python -m release_contract.cli import counts.csv \
  --product "checkout-assistant v7" -o contract.json
```

It needs `id`, `n`, `successes`; `volume_share`, `harm_if_wrong`, `fallback`,
`cost_per_case`, `human_review_cost` are optional (see
`examples/counts.example.csv`). A `success_rate` or `accuracy` column is
refused on purpose — a rate without its denominator cannot be audited, and an
unknown column is an error so a typo cannot become a silent default.

After the launch, close the loop on the trigger `decide` recorded:

```bash
python scripts/check_rollback_baseline.py contract.json run_log.jsonl \
  --window-size 200 --fail-on-trigger     # exit 2 if an AUTO segment drifted
```

Log one `{"segment": "...", "ok": true|false}` line per handled case, in order.
A case with no outcome may omit `ok`: it is skipped and counted, never treated
as a failure. A partial window never fires, and a segment absent from the log is
reported as `no observations` rather than looking healthy.

## Contract schema

```json
{
  "product": "checkout-assistant v7",
  "guardrails": {
    "min_sample_size": 100,
    "min_success_rate": 0.9,
    "max_harm": "medium",
    "max_cost_per_case": 0.5,
    "z": 1.96
  },
  "segments": [
    {
      "id": "routine_faq",
      "volume_share": 0.6,
      "n": 400,
      "successes": 388,
      "harm_if_wrong": "low",
      "fallback": "none",
      "cost_per_case": 0.02,
      "human_review_cost": 0.0
    }
  ]
}
```

| field | type | rule |
|---|---|---|
| `product` | string | non-empty; what is being released |
| `guardrails.min_sample_size` | int | ≥ 1 |
| `guardrails.min_success_rate` | float | 0–1; the bar the **lower bound** must clear |
| `guardrails.max_harm` | enum | `low` / `medium` / `high` / `critical` |
| `guardrails.max_cost_per_case` | float | ≥ 0 |
| `guardrails.z` | float | > 0; 1.96 = 95% one-sided, 2.33 = 99% |
| `segments[].id` | string | unique, non-empty |
| `segments[].volume_share` | float | 0–1; **sum over all segments ≤ 1.0** |
| `segments[].n` | int | ≥ 0; the denominator, never chosen by the caller |
| `segments[].successes` | int | 0 ≤ `successes` ≤ `n` |
| `segments[].harm_if_wrong` | enum | `low` / `medium` / `high` / `critical` |
| `segments[].fallback` | enum | `none` / `human` / `degrade` / `rollback` |
| `segments[].cost_per_case` | float | ≥ 0 |
| `segments[].human_review_cost` | float | ≥ 0; loaded cost of the fallback |

Unknown keys are rejected on purpose: a typo must not silently become a
default. Declared shares may sum to less than 1.0 — the remainder is reported
as `uncovered`, never dropped. Claiming more than 1.0 is refused.

Three rules that are easy to trip over:

- **Numbers must be finite.** `NaN` and `Infinity` are refused at parse time.
  They are not pedantry: `NaN` compares False against every threshold, so a NaN
  cost would sail through the cost gate and release the segment.
- **Counts are integers, not strings or booleans.** `"n": "200"` and
  `"n": true` are rejected with a readable message rather than a Python error.
- **`guardrails` may be omitted** and then takes the documented defaults above.
  Whatever is in force is echoed in `decide --json` under `guardrails`, so a
  decision always records the thresholds it was made under. A BOM in front of
  the JSON is tolerated (Excel and Notepad add one); a `min_success_rate` of
  `0` is obeyed but flagged as `success_floor_is_zero`, because it makes gate G2
  vacuous.

## The six gates

| gate | effect |
|---|---|
| `G1_SAMPLE` | `n` below `min_sample_size` → `HOLD` (missing evidence, not a failure) |
| `G2_WILSON` | Wilson lower bound below `min_success_rate` → `FENCE` |
| `G3_HARM` | `harm_if_wrong` above `max_harm` → `FENCE`, regardless of accuracy |
| `G4_FALLBACK` | high/critical harm with `fallback=none` → `FENCE` |
| `G5_COST` | load cost including human fallback above budget → `FENCE` |
| `G6_COVERAGE` | global: undeclared traffic is reported, never hidden |

Strictness is `HOLD > FENCE > AUTO`. Every triggered gate is printed with its
reason, so a NO-GO can be argued with instead of just accepted.

`G2` is the one people fight about. At `n=30, successes=30` the observed rate
is 1.000 but the Wilson lower bound is 0.8865, below a 0.9 bar: zero observed
failures is not proof. Two segments with the same 0.970 point estimate can get
opposite verdicts purely because their interval widths differ.

## Output

- Per-segment verdict plus every triggered gate and its reason.
- Four traffic buckets that always sum to 1.0: `auto` / `fence` / `hold` /
  `uncovered`.
- Evidence-risk flags (`uncovered_traffic`, `threshold_hugging`,
  `no_failure_observed`, `uniform_sample_sizes`, `zero_cost`) — **advisory
  only**, they never change a verdict.
- A rollback trigger per `AUTO` segment: the observed rate that would drop it
  below its gate.
- `--json` gives stable keys for a CI golden diff.
- `diff` reports per segment: regression / improvement / unchanged / added /
  removed, plus the traffic delta.

## Exit codes

| code | meaning | what to do |
|---|---|---|
| 0 | decided, nothing the caller opted into was hit | read the verdicts |
| 2 | `--fail-on` / `--fail-on-regression` matched | stop the pipeline; inspect that segment |
| 3 | missing file, malformed JSON, or rejected contract | fix the input; the message names the field |

Errors print one line on stderr. A traceback means a bug in this skill — report
it, do not work around it.

Other commands, for orientation rather than for the main flow:

```bash
python -m release_contract.cli gates     # list the six gates and the strictness order
python -m release_contract.cli eval      # run the bundled suites (synthetic, not a score to cite)
python -m release_contract.cli version   # print version
```

## Reading the result honestly

- `AUTO` is a claim about **evidence**, not about the world. It says: given
  these counts, this segment is not the one that will embarrass us.
- A `FENCE` on high harm is not a quality verdict; a 99% accurate segment can
  still be fenced because the 1% is unrecoverable.
- If a reviewer disagrees with `G2` itself (they want point-estimate
  semantics), that is a **scope disagreement**, not a bug. Say so and stop.
- The gate list shows **every** gate that failed, while the verdict comes from
  the primary one. A `HOLD` segment can therefore still list a `FENCE`-class
  gate — most visibly on a fresh `init`, where `n=0` fails `G1` (no evidence)
  and `G2` (0.0 below the floor) at the same time. Read the verdict, then read
  the gates to see why.
- `diff` compares two contracts; if the guardrails changed too, the comparison
  is not apples to apples — check `guardrails` first.

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `invalid counts: success_rate: a rate without its denominator...` | the CSV carried a rate column | export `n` and `successes` from the eval run instead |
| `invalid counts: unknown column(s)` | typo or an extra export column | keep only the documented columns |
| `invalid contract: unknown contract keys` | typo or extra key | run `init` again and diff the key names |
| `declared volume_share sums to ... > 1.0` | shares double-counted | the denominator is full traffic; lower the shares |
| everything is `HOLD` | `n` below `min_sample_size` | gather more cases, or lower the bar **and say so** |
| an expected `AUTO` became `FENCE` | Wilson lower bound, not the point estimate | `python -m release_contract.cli decide --json` and read `wilson_lower` |
| `--fail-on` never fires | verdict names are case-insensitive but must be `AUTO`/`FENCE`/`HOLD` | check the argument |

## Files

| path | what it is |
|---|---|
| `release_contract/engine.py` | deterministic gates, Wilson bound, traffic accounting |
| `release_contract/report.py` | text and stable-key JSON rendering |
| `release_contract/diff.py` | version-to-version segment diff |
| `release_contract/properties.py` | invariant scan that needs no golden labels |
| `examples/` | fabricated demo contracts (labelled SYNTHETIC) |
| `examples/launch/` | synthetic runtime log and the post-launch baseline check, wired end to end |
| `DESIGN.md` | each decision beside the alternative it beat, plus two open rule questions and their measured cost |
| `scripts/whatif_rules.py` | prices those two open questions in verdicts; implements neither |
| `assets/demo-recording.gif` | a real screen capture of one demo run; `assets/demo-recording.json` carries its hash |
| `assets/demo.gif` | the README animation, rendered from live stdout by `scripts/render_demo_gif.py` (not a screen capture) |
| `eval/` | self-built dev/hold-out suites and the blind protocol |

## Boundaries (read before citing any number)

- The engine calls no LLM, no network and no randomness. Same JSON in,
  byte-identical decision out; that is what makes it auditable offline.
- The two bundled eval sets are **fabricated**, written by the rule author.
  Their perfect scores are a rule-consistency check, not real-world
  effectiveness. See `eval/README.md`.
- Three blind rounds are published, each with the sheet it was scored from:
  **0.8507** [0.7466, 0.9169], **0.9403** [0.8563, 0.9765], **0.7910**
  [0.6793, 0.8712], all on the same 67 segments. Pairwise kappa is 0.6554 /
  0.8929 / 0.7498, so quote the band, never one number. Every disagreement in all
  three rounds falls into one of two rule questions (10 Wilson-class cases, 4
  rule-class cases), with none unexplained: the three rates are exactly
  1 - 10/67, 1 - 4/67, 1 - 14/67. On both rule questions the engine is on the
  minority side — 2 of 3 readers disagree with it. See `DESIGN.md`.
- A fourth round ran on a **different** 38-segment set and scored **0.8947**
  [0.7587, 0.9583]. Its four disagreements are one question — whether
  `degrade` / `rollback` count as a fallback, and from which harm rank gate G4
  requires one (`DESIGN.md`, question 3). It is not comparable to the three
  rates above, and adopting that reading would make it agree 38/38, so it was
  not adopted.
- `scripts/property_scan.py` checks eight invariants over a fixed-seed
  parameter space without any golden label (traffic accounting, replay,
  Wilson and ablation monotonicity, invalid input, segment order, "more
  successes never stricter", "higher floor never looser"). It finds bugs; it
  cannot judge whether the gates reflect good product judgement. The scanner
  is itself tested with planted bugs, so a pass means the checks fire.
- No real launch data, no real users, no external annotation, and no measured
  accuracy for the evidence-risk flags exist in this project. The post-launch
  baseline check runs only on a fabricated log; whether a recorded Wilson
  baseline predicts real drift is unmeasured.
- This does not tell you whether your eval was well designed. A curated test
  set that hides messy edge cases still produces green verdicts — that is what
  the Goodhart flags are for.
- Upstream, `complaint-to-eval` answers "what should we test"; this skill
  answers "can we ship". Complementary, neither replaces the other.

Author: jian935 · MIT · Version 0.3.0
