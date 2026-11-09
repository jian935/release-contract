# Design decisions

Every choice below was made against an alternative that a reasonable person
would also propose. The alternatives are listed with the reason they lost, so
a future maintainer can reopen a decision with evidence instead of taste.

## 1. Raw counts in, never a rate

**Chosen:** the contract stores `n` and `successes`; the rate is derived.

**Rejected:** accepting `success_rate: 0.97`.

A caller who supplies a rate also supplies, implicitly, the denominator. That
is how "95% success" becomes 19 out of 20 cases chosen after the fact. Raw
counts make the denominator part of the input, so it can be argued with. This
is the same failure mode as a chosen benchmark subset; the fix is structural,
not a warning in the docs.

## 2. Wilson lower bound in gate G2, not the point estimate

**Chosen:** `AUTO` requires the **lower bound** of the Wilson interval to clear
`min_success_rate`.

**Rejected:** `successes / n >= min_success_rate`.

At `n=30, successes=30` the point estimate is 1.000 and the lower bound is
0.8865. A tool that accepts 30/30 as proof of 90% reliability has learned
nothing from the last decade of eval practice. The price is real and measured:
in blind round 1 every disagreement with an independent reader was this gate
(see `eval/blind/rounds/round1/`). We keep it, because "ship it, the rate was
97%" is exactly the sentence this tool exists to prevent.

If an organisation genuinely wants point-estimate semantics, the honest move
is to not use gate G2 — not to quietly widen the tool.

## 3. Four traffic buckets, denominator fixed at 1.0

**Chosen:** `auto / fence / hold / uncovered` always sum to 1.0; undeclared
traffic is shown as `uncovered` and a contract claiming more than 1.0 is
refused.

**Rejected:** reporting rates over "declared traffic only".

That is the same trick as an eval that only scores the cases it kept. A
partial contract is a partial contract: 60% of declared traffic could be 60%
of 10%. Fixing the denominator makes the omission visible instead of
arithmetically invisible.

## 4. `HOLD` is a first-class verdict

**Chosen:** `n < min_sample_size` returns `HOLD` (evidence missing), not
`FENCE` (evidence says no).

**Rejected:** collapsing everything into ship / no-ship.

`FENCE` and `HOLD` lead to different actions: `FENCE` means route to a human or
disable, `HOLD` means go get more cases. Merging them makes the report look
decisive while hiding the only actionable next step. Strictness order is
`HOLD > FENCE > AUTO` so a gate can never be talked down by another gate.

## 5. Deterministic engine, no LLM in the decision path

**Chosen:** pure functions, no network, no randomness; same JSON in,
byte-identical decision out.

**Rejected:** "let a model weigh the trade-offs".

A release decision that changes between runs cannot be audited, diffed in CI,
or argued with after an incident. Determinism also makes the property scan
possible (`scripts/properties.py`): if the engine can be replayed, invariants
can be asserted without a single golden label.

## 6. Evidence-risk flags are advisory only

**Chosen:** `uncovered_traffic`, `threshold_hugging`, `no_failure_observed`,
`uniform_sample_sizes`, `zero_cost` are printed but never change a verdict.

**Rejected:** letting a Goodhart flag downgrade an `AUTO`.

Two failure modes trade off here. A downgrading flag would be defensible, but
it would also make the tool tunable: anyone could silence an inconvenient
`FENCE` by adjusting whichever flag caused it, and nobody could tell the
difference from the outside. Advisory flags keep the verdict chain auditable —
every verdict traces to a named gate with a numeric reason.

## 7. Self-written eval sets, labelled as such

**Chosen:** `eval/dev.jsonl` and `eval/holdout.jsonl` are fabricated and scored
1.0000; the READMEs say in three places that this is a rule-consistency number,
not effectiveness.

**Rejected:** presenting that 1.0000 as accuracy.

The labels were written by the same person who wrote the gates, one branch per
gate, so a perfect score is arithmetic, not evidence. The honest alternative to
a fake number is a smaller real one: blind round 1 against an independent
reader, published with its sheet and interval.

## 8. Strict loader that rejects unknown keys

**Chosen:** a typo like `sucesses` raises an error instead of defaulting to 0.

**Rejected:** lenient parsing with defaults.

Silent defaults are how a contract quietly becomes evidence-free: `n=0` still
produces a verdict, and an `AUTO` on a misspelled field would look legitimate.
Failing loudly is cheaper than a post-incident archaeology session.

## What would change these decisions

- **G2:** a real launch history showing that segments which cleared the
  *point estimate* but not the lower bound never needed a rollback. That is
  measurable and we have not measured it.
- **Determinism:** nothing short of a requirement to incorporate non-replayable
  human judgement in the decision itself. Even then, the deterministic core
  should stay and the human input should enter as declared evidence.
- **Advisory-only flags:** evidence that a specific flag predicts harm on its
  own, which would justify promoting it to a gate with its own threshold.
