# Changelog

Numbers here are measurements from this repository, not marketing. Anything
not measured is marked as such.

## Unreleased

- Published blind round 2 under `eval/blind/rounds/round2/`: sheet, frozen
  result, and a record of the four disagreements. Agreement **0.9403**, Wilson
  95% [0.8563, 0.9765] over the same 67 segments, from a second independent
  reader. Reader-vs-reader agreement is 0.791 raw / Cohen's kappa 0.6554, so the
  two rates are now always quoted together.
- Round 2's reader applied a Wilson lower bound unprompted; 12 rationales quote
  it and all 12 match `wilson_lower` within 0.05pp. G2 is therefore no longer the
  contested gate — the remaining four disagreements are rule precedence
  (fallback vs harm ceiling; `HOLD` vs `FENCE` when evidence is thin *and* a hard
  ceiling is violated), written up as open questions in `DESIGN.md`.
- The published-round self-check now requires **every** round's rate to be
  quoted in all three public docs, not just the newest one, so a better number
  cannot bury a worse one.
- Added `assets/demo-recording.gif`: a real screen capture of one run (26 s,
  800px, console window only) with `assets/demo-recording.json` holding its
  SHA-256, the host and exactly what was scaled. A new self-check fails when the
  sidecar and the file disagree, because a capture cannot be regenerated.
- `scripts/demo.py` now invokes `sys.executable` instead of `python`. A Windows
  launcher stub could shadow `python`, exit 0 and print nothing, which produced
  a recording of four commands with no output. It also prints a warning when a
  step succeeds while printing nothing, so that failure can no longer be silent.
- The last demo step reports its real exit code instead of printing the report a
  second time; the duplicated report pushed the verdict table out of view.
- The README animation is `assets/demo.gif`, rendered from real stdout by
  `scripts/render_demo_gif.py`. A SHA-256 sidecar lets the self-check fail when
  the engine changes without re-rendering — it is a rendering, not a screen
  capture, and it says so in both the README and the sidecar.

## 0.2.0 — 2026-11-09

**Usable as a skill, not just a script.**

- Added `init`: writes a structurally valid starter contract whose `n=0`
  makes it decide `HOLD`. A fresh user can reach a first decision without
  reading the schema by hand.
- Added `validate`: checks structure, enum values and coverage without
  deciding, with `--json` for tooling.
- Added `import`: builds a contract from a CSV of raw counts (`id`, `n`,
  `successes`, optional segment fields). A `success_rate` / `accuracy` column
  is refused with the reason, and unknown columns are errors, so a typo cannot
  become a silent default. `examples/counts.example.csv` shows the shape.
- Added `--version` and `version`; `diff --fail-on-regression` returns exit 2
  when any segment got worse.
- Exit codes are now a documented interface: `0` ok, `2` opted-in gate hit,
  `3` unusable input. Invalid input prints one line on stderr instead of a
  traceback.
- `pyproject.toml` added: `pip install .` provides a `release-contract`
  console script. Version must now agree across `__init__.py`, both READMEs
  and `pyproject.toml`; the self-check fails otherwise.
- `SKILL.md` rewritten as an agent runbook: four-step workflow, field table
  with ranges and enums, exit-code table, troubleshooting table.
- Added `DESIGN.md`: each decision paired with the alternative it beat and the
  evidence that would reopen it.
- Property scan grew from five to eight invariants: segment-order invariance,
  "more successes never make a verdict stricter", and "raising
  `min_success_rate` never loosens a verdict". The scanner now accepts an
  injected decider so tests can plant a bug and prove the checks fire.
- Blind round 1 published under `eval/blind/rounds/round1/`: sheet, frozen
  result and a self-check that recomputes the published rate from the sheet
  and fails on drift. Agreement 0.8507, Wilson 95% [0.7466, 0.9169] over 67
  segments; all ten disagreements are the Wilson gate and none runs in the
  dangerous direction.
- Added `scripts/compare_rounds.py`: inter-annotator agreement (raw + Cohen's
  kappa) on the segments two rounds share, so a second reader can tell
  "conservative tool" apart from "one reader's habit".
- Added `scripts/logs_to_counts.py`: runtime JSONL (`segment`, `ok`) to the
  counts CSV that `import` consumes. Records without an outcome are excluded
  from `n` and reported, never counted as failures.
- Added `scripts/demo.py`: paced replay of the flow for screen recording.

## 0.1.0 — 2026-11-08

Initial local build.

- Six deterministic gates, Wilson lower bound instead of the point estimate,
  four traffic buckets that always sum to 1.0.
- `decide` / `diff` / `gates` / `eval` / `version`, `--fail-on`, `--json`.
- Self-built dev/hold-out suites: 25 cases each, 32 and 35 scored segments,
  verdict accuracy 1.0000 with Wilson 95% [0.8928, 1.0] and [0.9011, 1.0].
  These are rule-consistency numbers from author-written labels, not
  effectiveness evidence.
- Property scan over a fixed seed, blind protocol, answer-free packets and a
  release self-check suite.
