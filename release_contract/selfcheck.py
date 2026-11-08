"""Release self-checks. Single source of truth for both CI and the test suite.

Checks assert *labels and structure*, never hard-coded scores or counts: a
changing eval result must not break the build. Deliberately unmeasured items
are declared, not silently treated as passing.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".txt", ".cfg", ".toml",
}
SKIP_DIRS = {".git", "__pycache__", ".local", ".pytest_cache", ".venv", "venv"}
PERSONAL_EMAIL = re.compile(
    r"\b[\w.+-]+@(?:qq|163|126|gmail|outlook|foxmail|sina|sohu)\.com\b", re.I
)
MAINLAND_PHONE = re.compile(r"\b1[3-9]\d{9}\b")
ID_NUMBER = re.compile(r"\b\d{17}[\dXx]\b")


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _read(path: Path) -> str:
    # A missing file must surface as a FAILED check, not a crashing build.
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _tracked_text_files() -> list[Path]:
    """Approximate ``git ls-files`` without requiring a git checkout."""
    out: list[Path] = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            p = Path(base) / name
            if p.suffix.lower() in TEXT_SUFFIXES:
                out.append(p)
    return out


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _check(name: str, ok: bool, detail: str) -> Check:
    return Check(name=name, ok=bool(ok), detail=detail)


def run_checks() -> list[Check]:
    checks: list[Check] = []

    # 1. Version appears in three places and agrees.
    init_text = _read(ROOT / "release_contract" / "__init__.py")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    version = m.group(1) if m else ""
    en = _read(ROOT / "README.md")
    zh = _read(ROOT / "README.zh-CN.md")
    checks.append(
        _check(
            "version_sync",
            bool(version)
            and (("Version: %s" % version) in en)
            and (("Version: %s" % version) in zh or ("版本：%s" % version) in zh),
            "version %s must appear in __init__.py and both READMEs" % (version or "MISSING"),
        )
    )

    # 2. Every number in one README must appear in the other. No chosen denominator.
    diff = _numbers(en) ^ _numbers(zh)
    checks.append(
        _check(
            "readme_number_symmetry",
            not diff,
            "numbers present in only one README: %s" % (sorted(diff) if diff else "none"),
        )
    )

    # 3. Mutual links.
    checks.append(
        _check(
            "readme_crosslink",
            "README.zh-CN.md" in en and "README.md" in zh,
            "English and Chinese READMEs must link to each other",
        )
    )

    # 4. CLI commands <-> documented commands, both directions.
    from .cli import COMMANDS

    missing = [c for c in COMMANDS if ("cli %s" % c) not in en or ("cli %s" % c) not in zh]
    documented = set(re.findall(r"release_contract\.cli\s+(\w+)", en + zh))
    undocumented = sorted(documented - set(COMMANDS))
    checks.append(
        _check(
            "cli_commands_documented",
            not missing and not undocumented,
            "undocumented commands=%s; documented-but-missing=%s"
            % (missing, undocumented),
        )
    )

    # 5. Synthetic data is labelled, and the eval README explains why it looks good.
    demo = _read(ROOT / "examples" / "demo_contract.json")
    eval_readme = _read(ROOT / "eval" / "README.md")
    labelling = ("SYNTHETIC" in demo or "fabricated" in demo.lower()) and (
        "fabricated" in eval_readme.lower() or "编造" in eval_readme
    )
    explanation = ("why" in eval_readme.lower() or "为什么" in eval_readme)
    checks.append(
        _check(
            "synthetic_data_labelled",
            labelling and explanation,
            "demo must be labelled fabricated and eval/README.md must explain why it scores well",
        )
    )

    # 6. Honest boundary: unmeasured items must be declared in both READMEs.
    declared = all(
        (("not measured" in t.lower()) or ("未测" in t) or ("没有真实" in t))
        for t in (en, zh)
    )
    checks.append(
        _check(
            "unmeasured_declared",
            declared,
            "both READMEs must state what has NOT been measured",
        )
    )

    # 7. No personal data in any text file that would be packaged.
    leaks: list[str] = []
    for p in _tracked_text_files():
        text = _read(p)
        for label, pattern in (
            ("phone", MAINLAND_PHONE),
            ("personal_email", PERSONAL_EMAIL),
            ("id_number", ID_NUMBER),
        ):
            if pattern.search(text):
                leaks.append("%s:%s" % (p.relative_to(ROOT), label))
    checks.append(
        _check(
            "privacy_scan",
            not leaks,
            "personal-data matches: %s" % (leaks if leaks else "none"),
        )
    )

    # 8. Packaging must never include .git, caches or local-only data.
    rels = [str(p.relative_to(ROOT)).replace("\\", "/") for p in _tracked_text_files()]
    forbidden = [
        r for r in rels
        if r.startswith(".git/")
        or "__pycache__" in r
        or r.startswith(".local/")
        or r.endswith(".pyc")
    ]
    checks.append(
        _check(
            "package_manifest",
            not forbidden,
            "forbidden packaged paths: %s" % (forbidden if forbidden else "none"),
        )
    )

    # 9. Both eval suites exist, are non-empty, and use distinct case ids.
    from .evalset import SUITES, load_cases, run_suite

    ids: dict[str, set[str]] = {}
    kinds: dict[str, set[str]] = {}
    for which in SUITES:
        cases = load_cases(which)
        ids[which] = {c["id"] for c in cases}
        kinds[which] = {c["kind"] for c in cases}
    dev_ids, ho_ids = ids.get("dev", set()), ids.get("holdout", set())
    checks.append(
        _check(
            "eval_suites_distinct",
            bool(dev_ids)
            and bool(ho_ids)
            and not (dev_ids & ho_ids)
            and kinds.get("dev") == kinds.get("holdout"),
            "dev/hold-out must share structural kinds but not case ids",
        )
    )

    # 10. Suites must run; the score itself is reported, never asserted.
    results = {w: run_suite(w) for w in SUITES}
    checks.append(
        _check(
            "eval_suites_runnable",
            all(r["scored_segments"] > 0 for r in results.values()),
            "scored segments: %s"
            % {w: r["scored_segments"] for w, r in results.items()},
        )
    )

    # 11. Symmetry alone is not enough: both READMEs could agree on a stale
    # number. Compare their eval tables against the live suite output.
    def _eval_rows(text: str) -> dict[str, list[str]]:
        rows: dict[str, list[str]] = {}
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("| dev |") or s.startswith("| holdout |"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                rows[cells[0]] = cells
        return rows

    stale: list[str] = []
    for which, r in results.items():
        ci = r["wilson95_ci"]
        expected_row = [
            which,
            str(r["cases"]),
            str(r["scored_segments"]),
            "%.4f" % r["accuracy"],
            "[%s, %s]" % (ci[0], ci[1]) if ci else "n<8, no interval",
        ]
        for label, text in (("README.md", en), ("README.zh-CN.md", zh)):
            actual = _eval_rows(text).get(which)
            if actual != expected_row:
                stale.append(
                    "%s/%s got %s, expected %s" % (label, which, actual, expected_row)
                )
    checks.append(
        _check(
            "readme_eval_numbers_fresh",
            not stale,
            "stale eval numbers: %s" % (stale if stale else "none"),
        )
    )

    # 12. The Skill entry point must be installable and must not drift from
    # the CLI it documents.
    skill = _read(ROOT / "SKILL.md")
    parts = skill.split("---", 2)
    front = parts[1] if len(parts) >= 3 and skill.startswith("---") else ""
    fm_ok = "name: release-contract" in front and "description:" in front
    skill_cmds = set(re.findall(r"release_contract\.cli\s+(\w+)", skill))
    unknown_cmds = sorted(skill_cmds - set(COMMANDS))
    checks.append(
        _check(
            "skill_frontmatter_and_commands",
            fm_ok and not unknown_cmds,
            "frontmatter=%s; unknown commands=%s" % (fm_ok, unknown_cmds),
        )
    )

    return checks


def render(checks: list[Check]) -> str:
    lines = ["release-contract self-check"]
    for c in checks:
        lines.append("  [%s] %-28s %s" % ("PASS" if c.ok else "FAIL", c.name, c.detail))
    lines.append(
        "  %d/%d passed" % (sum(1 for c in checks if c.ok), len(checks))
    )
    lines.append(
        "  NOTE: all-green is not proof of no gaps; declared unmeasured items stay unmeasured."
    )
    return "\n".join(lines)
