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

## Open questions the blind rounds exposed

Both came from round 2 and neither is patched to match the reader. They are
listed here because *changing them would invalidate every published round*, so
they need a deliberate decision and a full re-run, not a quiet edit.

### 1. Does an existing human fallback relax the harm ceiling?

- **Evidence:** `rounds/round2` dev-008 and dev-009. The reader saw `harm=high`
  (and `critical`) against a `medium` ceiling, noticed a human fallback was
  configured, and answered `AUTO`; the engine answers `FENCE` via G3.
- **Position today:** the ceiling is absolute. It describes how bad being wrong
  is; a fallback changes who catches it, not how bad it is.
- **Counter-position:** if every error is caught by a human anyway, the realised
  harm may be `low`, and refusing outright over-blocks a segment that could
  safely run at reduced automation.
- **What would settle it:** a launch where fenced-but-fallback segments show a
  materially different realised harm than their declared `harm_if_wrong`. Then
  either G3 gains a `fallback_adjusted_harm` input or the docs stop calling the
  ceiling absolute.
- **Measured cost today:** over the 67 published blind segments, lowering
  effective harm by one rank for any configured fallback would move **3**
  segments from `FENCE` to `AUTO` — `dev-008`, `ho-008`, `ho-012`
  (`python scripts/whatif_rules.py`). Under that one-rank reading, `dev-009` —
  the second case the same reader disputed — would *still* be fenced, because
  `critical` minus one rank is above a `medium` ceiling. To reproduce both of
  that reader's verdicts the rule has to be "a fallback removes the ceiling
  entirely", which is a much stronger claim and would need a harm model, not a
  rank shift.

### 2. When evidence is thin *and* a hard ceiling is violated, `HOLD` or `FENCE`?

- **Evidence:** `rounds/round2` dev-020 and ho-020. `n=50` (and `n=10`) against a
  `min_sample_size` of 100, *plus* a critical harm with no fallback. G1 fires
  first, so the engine says `HOLD`; the reader said `FENCE`.
- **Why the reader may be right:** more data cannot fix an absolute ceiling
  violation. Telling someone `HOLD` sends them off to collect samples that cannot
  change the answer.
- **Why the ordering exists:** `HOLD` is defined as "the evidence cannot support
  a verdict", and a 50-sample segment genuinely cannot. Reporting a hard gate the
  sample size makes unmeasurable is a different claim.
- **Cost of changing:** verdict precedence touches every gate combination. All
  50 golden cases would need re-deriving, and both published rounds would need
  re-scoring — at which point the published numbers change and the changelog has
  to say so.
- **Measured cost today:** over the 67 published blind segments, letting a hard
  violation outrank `G1` would move exactly **2** segments from `HOLD` to
  `FENCE` — `dev-020` and `ho-020`, which are precisely the two the reader
  disputed (`python scripts/whatif_rules.py`). Unlike the harm-ceiling question,
  this one is cheap in verdicts; it is expensive only in published numbers.

Neither question justifies changing the engine on the strength of one reader.
The second one does justify a documentation fix, which is in place: `HOLD` is
described as "not enough evidence", never as "safe to ship".

## What would change these decisions

- **G2:** a real launch history showing that segments which cleared the
  *point estimate* but not the lower bound never needed a rollback. That is
  measurable and we have not measured it.
- **Determinism:** nothing short of a requirement to incorporate non-replayable
  human judgement in the decision itself. Even then, the deterministic core
  should stay and the human input should enter as declared evidence.
- **Advisory-only flags:** evidence that a specific flag predicts harm on its
  own, which would justify promoting it to a gate with its own threshold.
