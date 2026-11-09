# Next batch: cases nobody has annotated

`sheet.csv` is a second, independent packet of **30 contracts / 38 segments**
that have never been shown to a reader. It is blank. No round has been run on
it, so it has no agreement figure and none may be quoted.

## Why a new batch instead of a fourth round on the old one

Rounds 1, 2 and 3 all used the same 67 segments, and all three disagreements
decomposed into two named rule questions. A fourth reader on that sheet buys one
kappa point. It cannot reveal a third rule question, because the inputs are
fixed. New inputs can.

The first batch was also thin in specific places. Counted over its 67 segments,
four input shapes it never tested at all:

| input dimension | first batch | this batch |
|---|---|---|
| contracts with four segments | 0 | 1 |
| `n = 0` (no evidence at all) | 0 | 1 |
| `fallback` = degrade / rollback **and** `human_review_cost > 0` | 0 | 2 |
| ceiling set to something other than `medium` (cases) | 6 | 10 |

Three cases are deliberate **pairs**, which is where this batch is worth more
than its row count:

- `nb-07` / `nb-08` / `nb-09` share n, successes, harm and the 0.6 review cost,
  and differ only in `fallback`. Only `human` adds that review cost to the
  per-case cost, so two of the three are released at a real cost of 0.62 against
  a 0.5 cap while the third is fenced. Whether that is right is a judgement
  question, not a bug report — it is written down as such, not patched.
- `nb-18` / `nb-19` share 100/95 and differ only in the floor (0.9 vs 0.88).
- `nb-13` / `nb-14` / `nb-15` are n = 99 / 100 / 101 against a 100 floor.

Each case was chosen for one input dimension; the generator records that choice
in `scripts/gen_next_batch.py` as `covers`. It is a maintenance note and is
never written to `prompts.jsonl` or the sheet — the self-check fails if it ever
appears in either.

## What this batch can and cannot measure

- **Can:** whether a third rule question exists behind the two documented ones,
  and whether readers price `degrade` / `rollback` the way G5 does (only
  `human` has its review cost loaded into the per-case cost).
- **Cannot:** be compared with rounds 1–3 as if it were the same measurement.
  These cases were **selected for coverage, not sampled at random**, and the
  readers have not seen them. A different agreement rate here is expected and is
  not evidence that the engine got better or worse. Report it as a separate
  number, with this paragraph attached.
- **Cannot:** say anything about real launch outcomes. Every number is
  fabricated. Nothing in this repository has been validated against a live
  release.

## Coordinator workflow

Hand the reader **only** `sheet.csv`. Do not hand them this file, `prompts.jsonl`,
or anything under `rounds/`.

```bash
# score a returned sheet against this batch's prompts, without publishing
python scripts/blind_eval.py path/to/returned.csv \
  --prompts eval/blind/next_batch/prompts.jsonl

# freeze it, if you decide to publish it
python scripts/publish_round.py --round 4 \
  --prompts eval/blind/next_batch/prompts.jsonl \
  --sheet eval/blind/rounds/round4/answers.csv \
  --out   eval/blind/rounds/round4/result.json \
  --date  YYYY-MM-DD \
  --annotator "fifth reader; declared not to have seen any published round"
```

Without `--prompts`, both scripts read the first batch's prompt file and will
reject every row of this sheet as an unknown case id. That failure is deliberate:
silently scoring a new sheet against the old prompts would drop rows and report
a smaller denominator.

## Regenerating

```bash
python scripts/gen_next_batch.py
```

Single source of truth is that script. Do not hand-edit `prompts.jsonl` or
`sheet.csv`. Two self-checks hold the outputs in place: the prompts must stay
answer-free and share no case id or segment name with the first batch, and the
sheet must stay blank with the same 15 columns as `../盲评填写表.csv`.

## Admission rules for a reader

Same as `../next_round/README.md`: do not read `../rounds/`, do not read the
results section of the project README, do not run the CLI, do not discuss these
cases with someone who has. This batch is unlabelled, so a reader who has seen
nothing at all is easy to find — but they must also not see the engine output
afterwards, or the second round on this batch is contaminated.
