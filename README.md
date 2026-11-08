# release-contract

Decide which traffic segments of an AI product the offline evidence is strong
enough to release to — deterministically, with every gate visible.

Version: 0.1.0 · MIT · [中文说明](README.zh-CN.md)

> Not an eval framework: it does not measure quality. It decides where the
> existing evidence justifies letting the model act alone.

## Scope

Upstream, `complaint-to-eval` answers "what should we test"; this skill
answers "can we ship". They are complementary: one produces case candidates,
the other decides whether the evidence is strong enough to release.

## Why

One headline eval number cannot answer a launch question. A contract splits
traffic into segments and asks, per segment: automate, fence, or wait?
Averaging everything into one green score hides the expensive blind spot.

Offline results must be reported as raw counts. At n=30, successes=30 the
observed rate is 1.000, but the Wilson lower bound is 0.8865 — below the 0.9
bar — so zero observed failures is still not proof. Two segments with the
same 0.970 point estimate can get opposite verdicts purely because their
interval widths differ.

| n | successes | observed | Wilson lower |
|---|---|---|---|
| 30 | 30 | 1.000 | 0.8865 |
| 400 | 388 | 0.970 | 0.9483 |
| 1000 | 970 | 0.970 | 0.9575 |

## 30-second example

```
python -m release_contract.cli decide examples/demo_contract.json
```

```
SEGMENTS
  routine_faq            AUTO   share= 60.0%  observed=0.970  wilson_lower=0.948  cost=0.020
  billing_dispute        HOLD   share= 25.0%  observed=0.983  wilson_lower=0.911  cost=0.850
  contract_redline       FENCE  share= 10.0%  observed=0.990  wilson_lower=0.971  cost=0.030

TRAFFIC (denominator = full traffic 1.0)
  auto         60.0%
  fence        10.0%
  hold         25.0%
  uncovered     5.0%
  total       100.0%
```

The demo is fabricated (SYNTHETIC DEMO) and deliberately shows a partial
release: 60.0% AUTO, 25.0% HOLD, 10.0% FENCE, 5.0% undeclared traffic.

## The 6 gates

| gate | effect |
|---|---|
| G1_SAMPLE | n below min_sample_size → HOLD (missing evidence, not a failure) |
| G2_WILSON | Wilson lower bound below min_success_rate → FENCE |
| G3_HARM | harm_if_wrong above max_harm → FENCE, regardless of accuracy |
| G4_FALLBACK | high-harm segment with fallback=none → FENCE |
| G5_COST | loaded cost including human fallback above budget → FENCE |
| G6_COVERAGE | global: undeclared traffic is reported, never hidden |

Strictness is HOLD > FENCE > AUTO. Every triggered gate is printed with its
reason, so a NO-GO can be argued with instead of just accepted. The four
traffic buckets always sum to full traffic 1.0, never to a chosen subset.

Evidence-risk flags are advisory and never change a verdict. Otherwise the
tool could be tuned to look good.

## Commands

| command | what it does |
|---|---|
| `python -m release_contract.cli decide examples/demo_contract.json` | human-readable decision |
| `python -m release_contract.cli decide examples/demo_contract.json --json` | stable-key JSON for golden diffs |
| `python -m release_contract.cli gates` | list the gates |
| `python -m release_contract.cli eval` | run dev and hold-out suites |
| `python -m release_contract.cli version` | print version |
| `python -m release_contract.cli diff examples/demo_contract.json examples/demo_contract_v2.json` | compare two versions segment by segment |

`decide --fail-on FENCE,HOLD` returns a non-zero exit code if any segment
hits a listed verdict, so a pipeline can gate on it.

## Eval sets

Two fabricated suites, grouped by structural kind rather than by keywords.
Scoring unit is the per-segment verdict; the denominator is printed.

| suite | cases | scored segments | verdict accuracy | Wilson 95% CI |
|---|---|---|---|---|
| dev | 25 | 32 | 1.0000 | [0.8928, 1.0] |
| holdout | 25 | 35 | 1.0000 | [0.9011, 1.0] |

Both scores are 1.0000 because the golden labels were written by the author
of the rules, one branch per gate. That proves rule consistency and offline
replay, **not** real-world effectiveness. The intervals stay wide. See
`eval/README.md` for why it looks good, what is unscored, and the reverse
tests that prove each gate is load-bearing. Treat that table as a
**rule-consistency score**, not an effectiveness result or a headline number.

## Independent evidence

Two checks do not depend on author-written golden labels:

- `python scripts/property_scan.py` scans a fixed-seed parameter space and
  asserts invariants: traffic accounting, byte-identical replay, Wilson
  monotonicity, ablation monotonicity and invalid-input rejection. A
  violation is a bug, not a disagreeing label.
- `python scripts/blind_eval.py` compares an independent annotator with the
  engine using answer-free prompts in `eval/blind/`. See
  `eval/blind/README.md` for the protocol. Fill
  `answer_sheet.template.csv` and pass the CSV path to the script; undecided
  rows are skipped, never guessed.

**No blind evaluation has been run.** There is no measured agreement score,
and no number is claimed for it.

What would falsify this tool: an independent annotator systematically
disagreeing with `AUTO` verdicts on high-harm segments, or a real launch
where an `AUTO` segment needs a rollback far more often than its recorded
Wilson baseline predicts. Neither has been measured.

## Not measured

- No real launch data, no real users, no real model output, no external
  annotation. There is no measured accuracy for evidence-risk flags or for
  real launch outcomes.
- No independent annotator has labelled the blind prompts; there is no
  measured agreement score.
- The engine calls no LLM and no network; the same JSON produces a
  byte-identical decision. It cannot tell you whether your eval was well
  designed — a curated test set that hides edge cases still produces green
  verdicts.
- This is complementary to promptfoo / Langfuse (which run evals) and to
  ship-gate tools (which audit code and deployment). It replaces neither.

## Install

```
npx skills add jian935/release-contract
python scripts/quick_validate.py
```

Zero third-party dependencies. Python standard library only.

## License

MIT · Author: jian935
