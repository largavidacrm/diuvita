#!/usr/bin/env python3
"""Run the safe Diuvita CTO shadow cycle.

This orchestrates idempotent internal tools. It avoids public profile edits,
candidate draft promotion and auto-publication.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def try_parse_json(output: str) -> Any:
    text = output.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def run_step(name: str, args: list[str], timeout: int) -> dict[str, Any]:
    started = time.time()
    command = [sys.executable, str(SCRIPTS / args[0]), *args[1:]]
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    duration = round(time.time() - started, 2)
    return {
        "name": name,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "duration_seconds": duration,
        "summary": try_parse_json(result.stdout),
        "stdout_tail": result.stdout.strip()[-1200:],
        "stderr_tail": result.stderr.strip()[-1200:],
    }


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str], int]]:
    apply_flag = ["--apply"] if args.apply_safe else []
    return [
        (
            "capture_enrichment_review_claims",
            ["capture_enrichment_review_claims.py", "--limit", str(args.review_limit), *apply_flag],
            90,
        ),
        (
            "hydrate_source_records",
            [
                "hydrate_source_records.py",
                "--limit",
                str(args.source_limit),
                "--timeout",
                str(args.fetch_timeout),
                *apply_flag,
            ],
            max(90, args.source_limit * args.fetch_timeout + 30),
        ),
        (
            "monitor_source_changes",
            [
                "monitor_source_changes.py",
                "--limit",
                str(args.monitor_limit),
                "--timeout",
                str(args.fetch_timeout),
                *apply_flag,
            ],
            max(90, args.monitor_limit * args.fetch_timeout + 30),
        ),
        (
            "admin_digest",
            ["admin_digest.py", "--limit", str(args.digest_limit)],
            45,
        ),
        (
            "evaluate_claim_rules",
            ["evaluate_claim_rules.py", "--limit", str(args.claim_limit), "--json"],
            45,
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-safe", action="store_true", help="Run safe internal writes; never publish or edit clinics.")
    parser.add_argument("--review-limit", type=int, default=100)
    parser.add_argument("--source-limit", type=int, default=40)
    parser.add_argument("--monitor-limit", type=int, default=40)
    parser.add_argument("--digest-limit", type=int, default=8)
    parser.add_argument("--claim-limit", type=int, default=100)
    parser.add_argument("--fetch-timeout", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if min(args.review_limit, args.source_limit, args.monitor_limit, args.digest_limit, args.claim_limit) < 1:
        raise SystemExit("limits must be at least 1.")
    if args.fetch_timeout < 3 or args.fetch_timeout > 60:
        raise SystemExit("--fetch-timeout must be between 3 and 60 seconds.")

    steps = []
    for name, command_args, timeout in build_steps(args):
        step = run_step(name, command_args, timeout)
        steps.append(step)
        if not step["ok"]:
            break

    output = {
        "mode": "apply_safe" if args.apply_safe else "dry_run",
        "ok": all(step["ok"] for step in steps),
        "steps": steps,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
