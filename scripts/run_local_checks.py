#!/usr/bin/env python3
"""Run the local Diuvita safety checks used before commits."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEST_STEPS = [
    ("test: source snapshots", "scripts/test_capture_source_snapshot.py"),
    ("test: durable source rows", "scripts/test_source_snapshot_records.py"),
    ("test: publication rules", "scripts/test_diuvita_rules.py"),
    ("test: shadow extraction", "scripts/test_extract_clinic_profile_shadow.py"),
    ("test: shadow verification", "scripts/test_verify_clinic_profile_shadow.py"),
    ("test: review submission", "scripts/test_submit_shadow_extraction_review.py"),
    ("test: admin digest", "scripts/test_admin_digest.py"),
    ("test: enrichment claims", "scripts/test_capture_enrichment_review_claims.py"),
    ("test: candidate promotion gate", "scripts/test_promote_candidate_reviews.py"),
    ("test: source hydration", "scripts/test_hydrate_source_records.py"),
    ("test: source monitoring", "scripts/test_monitor_source_changes.py"),
    ("test: CTO shadow cycle", "scripts/test_run_cto_shadow_cycle.py"),
]

PYTHON_SCRIPTS = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "scripts").glob("*.py"))

ADMIN_JS_CHECK = r"""
const fs = require('fs');
const vm = require('vm');
const h = fs.readFileSync('admin/index.html', 'utf8');
const scripts = [...h.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
  .map(m => m[1])
  .filter(s => s.includes('(function ()'));
for (const s of scripts) new vm.Script(s);
console.log('OK admin JS syntax');
"""


@dataclass(frozen=True)
class CheckStep:
    label: str
    command: list[str]
    timeout: int


def print_output(title: str, text: str) -> None:
    clean = text.strip()
    if not clean:
        return
    print(f"{title}:")
    for line in clean.splitlines()[-80:]:
        print(f"  {line}")


def run_step(step: CheckStep) -> bool:
    started = time.time()
    print(f"RUN {step.label}", flush=True)
    result = subprocess.run(
        step.command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=step.timeout,
        check=False,
    )
    duration = round(time.time() - started, 2)
    if result.returncode == 0:
        print(f"OK  {step.label} ({duration}s)")
        return True
    print(f"FAIL {step.label} ({duration}s, exit {result.returncode})")
    print_output("stdout", result.stdout)
    print_output("stderr", result.stderr)
    return False


def build_steps(skip_build: bool) -> list[CheckStep]:
    steps: list[CheckStep] = [
        CheckStep("python syntax", [sys.executable, "-m", "py_compile", *PYTHON_SCRIPTS], 60),
    ]
    steps.extend(CheckStep(label, [sys.executable, script], 60) for label, script in TEST_STEPS)
    steps.append(CheckStep("clinic data validation", [sys.executable, "scripts/validate_data.py"], 60))
    if not skip_build:
        steps.append(CheckStep("static site build", [sys.executable, "build.py"], 120))
    steps.append(CheckStep("admin JavaScript syntax", ["node", "-e", ADMIN_JS_CHECK], 60))
    steps.append(CheckStep("whitespace check", ["git", "diff", "--check"], 60))
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true", help="Skip static site build.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    steps = build_steps(args.skip_build)
    for step in steps:
        if not run_step(step):
            return 1
    print(f"OK local checks: {len(steps)} checks passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
