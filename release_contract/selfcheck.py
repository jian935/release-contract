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

    # 1. Version appears in every place that can drift, and they all agree.
    init_text = _read(ROOT / "release_contract" / "__init__.py")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    version = m.group(1) if m else ""
    en = _read(ROOT / "README.md")
    zh = _read(ROOT / "README.zh-CN.md")
    pyproject = _read(ROOT / "pyproject.toml")
    pkg_version = ""
    if pyproject:
        pm = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject)
        pkg_version = pm.group(1) if pm else ""
    packaging_ok = (not pyproject) or (pkg_version == version)
    checks.append(
        _check(
            "version_sync",
            bool(version)
            and (("Version: %s" % version) in en)
            and (("Version: %s" % version) in zh or ("版本：%s" % version) in zh)
            and packaging_ok,
            "version %s must appear in __init__.py, both READMEs and pyproject (found %r)"
            % (version or "MISSING", pkg_version or "none"),
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

    # 13. Blind prompts must be answer-free and in sync with the scored sets.
    import importlib.util
    import json

    blind_path = ROOT / "eval" / "blind" / "prompts.jsonl"
    blind_rows = [
        json.loads(line) for line in _read(blind_path).splitlines() if line.strip()
    ]
    spec = importlib.util.spec_from_file_location(
        "gen_blind_prompts", ROOT / "scripts" / "gen_blind_prompts.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    rebuilt = gen.build_rows()
    leaked = [
        r.get("id", "?")
        for r in blind_rows
        if any(k in r for k in ("expected", "why", "kind"))
    ]
    in_sync = blind_rows == rebuilt
    checks.append(
        _check(
            "blind_prompts_answer_free_and_in_sync",
            bool(blind_rows)
            and not leaked
            and {r["id"] for r in blind_rows} == (dev_ids | ho_ids)
            and in_sync,
            "rows=%d leaked=%s in_sync=%s" % (len(blind_rows), leaked, in_sync),
        )
    )

    # 14. A published blind result must be reproducible from its own sheet, and
    #     the rate quoted in the docs must be that result. A number whose input
    #     nobody can re-run is the unfalsifiable claim this project rejects.
    import importlib.util as _ilu
    import json as _json

    blind_readme = _read(ROOT / "eval" / "blind" / "README.md")
    rounds_dir = ROOT / "eval" / "blind" / "rounds"
    round_dirs = (
        sorted(p for p in rounds_dir.iterdir() if p.is_dir())
        if rounds_dir.is_dir()
        else []
    )
    problems: list[str] = []
    rates: list[tuple[str, str]] = []

    if round_dirs:
        be_spec = _ilu.spec_from_file_location(
            "blind_eval_selfcheck", ROOT / "scripts" / "blind_eval.py"
        )
        be = _ilu.module_from_spec(be_spec)
        be_spec.loader.exec_module(be)
        for folder in round_dirs:
            sheet, frozen = folder / "answers.csv", folder / "result.json"
            if not sheet.exists() or not frozen.exists():
                problems.append("%s: missing answers.csv or result.json" % folder.name)
                continue
            try:
                published = _json.loads(_read(frozen))
            except ValueError as exc:
                problems.append("%s: result.json is not valid JSON (%s)" % (folder.name, exc))
                continue
            live = be.run(sheet)
            if live["status"] != "measured":
                problems.append("%s: sheet yields no score" % folder.name)
                continue
            for key in (
                "agreement",
                "wilson95_ci",
                "scored_segments",
                "correct",
                "annotated_cases",
                "disagreement_causes",
                "disagreements",
            ):
                if published.get(key) != live.get(key):
                    problems.append(
                        "%s/%s drifted: published=%r recomputed=%r"
                        % (folder.name, key, published.get(key), live.get(key))
                    )
            rates.append((folder.name, "%.4f" % live["agreement"]))

    if rates:
        latest_name, latest_rate = rates[-1]
        docs = {
            "README.md": en,
            "README.zh-CN.md": zh,
            "eval/blind/README.md": blind_readme,
        }
        for name, text in docs.items():
            if latest_rate not in text:
                problems.append(
                    "%s does not quote the published rate %s from %s"
                    % (name, latest_rate, latest_name)
                )
        detail = "rounds=%s; quoted rate=%s; problems=%s" % (
            [name for name, _ in rates],
            latest_rate,
            problems or "none",
        )
        ok = not problems
    else:
        # Nothing published yet: every public doc must say so, and no doc may
        # quote a rate.
        declared = [
            name
            for name, text in (
                ("README.md", en),
                ("README.zh-CN.md", zh),
                ("eval/blind/README.md", blind_readme),
            )
            if not re.search(r"(agreement\s*[:=]?\s*0\.\d)|(一致率\s*[:：=]?\s*0\.\d)", text, re.I)
        ]
        ok = len(declared) == 3 and "No blind evaluation has been run" in en
        detail = "no published rounds; docs quoting no rate=%d/3" % len(declared)

    checks.append(_check("blind_round_published_and_reproducible", ok, detail))



    # 15. Invariants that do not depend on any golden label.
    from .properties import scan as prop_scan

    props = prop_scan(trials=120)
    checks.append(
        _check(
            "property_invariants_hold",
            props["passed"],
            "%d violations over %d trials"
            % (len(props["violations"]), props["trials"]),
        )
    )

    # 16. The human annotation packet must stay answer-free and in sync.
    import csv
    import importlib.util
    import io

    packet_spec = importlib.util.spec_from_file_location(
        "gen_blind_packet", ROOT / "scripts" / "gen_blind_packet.py"
    )
    packet = importlib.util.module_from_spec(packet_spec)
    packet_spec.loader.exec_module(packet)
    rebuilt_ws, rebuilt_tpl = packet.build()
    ws_text = _read(ROOT / "eval" / "blind" / "worksheet.md")
    tpl_text = _read(ROOT / "eval" / "blind" / "answer_sheet.template.csv")
    guide_text = _read(ROOT / "eval" / "blind" / "ANNOTATOR_GUIDE.md")

    filled_rows = [
        r for r in csv.DictReader(io.StringIO(tpl_text))
        if (r.get("verdict") or "").strip()
    ]
    filled_cells: list[str] = []
    for line in ws_text.splitlines():
        if not line.startswith("| ") or "your verdict" in line:
            continue
        parts = line.split("|")
        if len(parts) >= 11 and parts[9].strip():
            filled_cells.append(line[:60])
    score_leaks = [
        text
        for text in (ws_text, tpl_text, guide_text)
        if any(s in text for s in ("1.0000", "0.8928", "0.9011"))
    ]
    in_sync = ws_text == rebuilt_ws and tpl_text == rebuilt_tpl
    checks.append(
        _check(
            "blind_packet_answer_free_and_in_sync",
            in_sync and not filled_rows and not filled_cells and not score_leaks,
            "in_sync=%s filled_rows=%d filled_cells=%d score_leaks=%d"
            % (in_sync, len(filled_rows), len(filled_cells), len(score_leaks)),
        )
    )

    # 17. The single handed-out CSV: self-contained, answer-free, in sync.
    single_spec = importlib.util.spec_from_file_location(
        "gen_single_sheet", ROOT / "scripts" / "gen_single_sheet.py"
    )
    single = importlib.util.module_from_spec(single_spec)
    single_spec.loader.exec_module(single)
    rebuilt_single = single.build()
    single_path = ROOT / "eval" / "blind" / "盲评填写表.csv"
    single_text = single_path.read_text(encoding="utf-8-sig", errors="replace")
    single_rows = list(csv.DictReader(io.StringIO(single_text)))
    single_filled = [
        r for r in single_rows if (r.get("你的判定") or "").strip()
    ]
    single_leaks = any(
        s in single_text for s in ("1.0000", "0.8928", "0.9011")
    )
    checks.append(
        _check(
            "single_sheet_answer_free_and_in_sync",
            single_text == rebuilt_single
            and bool(single_rows)
            and not single_filled
            and not single_leaks,
            "rows=%d in_sync=%s filled=%d score_leaks=%s"
            % (
                len(single_rows),
                single_text == rebuilt_single,
                len(single_filled),
                single_leaks,
            ),
        )
    )

    # 18. The round-2 handout must be the same answer-free sheet, still blank.
    #     Same cases keep inter-annotator agreement computable; a leaked score
    #     or a pre-filled cell would quietly invalidate the next round.
    next_sheet = ROOT / "eval" / "blind" / "next_round" / "sheet.csv"
    next_rows: list[dict] = []
    next_filled: list[dict] = []
    next_leaks = False
    next_synced = False
    if next_sheet.exists():
        next_text = next_sheet.read_text(encoding="utf-8-sig", errors="replace")
        next_rows = list(csv.DictReader(io.StringIO(next_text)))
        next_filled = [r for r in next_rows if (r.get("你的判定") or "").strip()]
        next_leaks = any(
            s in next_text for s in ("1.0000", "0.8928", "0.9011", "0.8507")
        )
        next_synced = next_text == rebuilt_single
    checks.append(
        _check(
            "next_round_sheet_ready_and_blank",
            bool(next_rows) and next_synced and not next_filled and not next_leaks,
            "rows=%d in_sync=%s filled=%d score_leaks=%s"
            % (len(next_rows), next_synced, len(next_filled), next_leaks),
        )
    )

    # 19. The README animation must be derivable from the current engine.
    #     A hash sidecar is used instead of re-rendering the GIF, so this check
    #     needs no Pillow and runs on every CI interpreter. A screenshot that
    #     outlives its code is the same lie as a stale number.
    import hashlib

    from .engine import decide, load_contract  # local import: keeps top clean
    from .report import render_text

    live_text = render_text(decide(load_contract(ROOT / "examples" / "demo_contract.json")))
    live_hash = hashlib.sha256(live_text.encode("utf-8")).hexdigest()
    recorded = ""
    try:
        meta = _json.loads(_read(ROOT / "assets" / "demo.gif.json"))
        recorded = str(meta.get("source_sha256", ""))
    except ValueError:
        recorded = ""
    gif_present = (ROOT / "assets" / "demo.gif").exists()
    checks.append(
        _check(
            "demo_asset_matches_live_output",
            gif_present and recorded == live_hash,
            "assets/demo.gif %s"
            % (
                "is in sync"
                if gif_present and recorded == live_hash
                else "is stale or missing; rerun scripts/render_demo_gif.py"
            ),
        )
    )

    # 20. The screen capture must carry a sidecar that matches the file on disk.
    #     A capture cannot be regenerated, so the sidecar is the only thing that
    #     ties the shipped GIF to the run that produced it.
    rec_gif = ROOT / "assets" / "demo-recording.gif"
    rec_meta_path = ROOT / "assets" / "demo-recording.json"
    rec_detail = "assets/demo-recording.gif missing"
    rec_ok = False
    if rec_gif.exists() and rec_meta_path.exists():
        try:
            meta = json.loads(rec_meta_path.read_text(encoding="utf-8"))
            actual = hashlib.sha256(rec_gif.read_bytes()).hexdigest()
            rec_ok = (
                meta.get("sha256") == actual
                and meta.get("bytes") == rec_gif.stat().st_size
                and meta.get("kind") == "real screen capture"
                and meta.get("not_a_rendering") is True
            )
            rec_detail = "hash %s" % ("matches" if meta.get("sha256") == actual else "DRIFTED")
        except (json.JSONDecodeError, OSError) as exc:
            rec_detail = "unreadable sidecar: %s" % exc
    checks.append(
        _check(
            "screen_recording_sidecar_matches",
            rec_ok,
            rec_detail,
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
