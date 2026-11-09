# Changelog

Numbers here are measurements from this repository, not marketing. Anything
not measured is marked as such.

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
