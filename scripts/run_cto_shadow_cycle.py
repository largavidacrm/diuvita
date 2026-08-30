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


STEP_ITEM_KEYS = {
    "capture_enrichment_review_claims": (
        "title",
        "review_id",
        "field_claims_created",
        "source_records_created",
    ),
    "hydrate_source_records": ("source_url", "status"),
    "monitor_source_changes": ("source_url", "clinic_name", "status", "hash"),
    "process_source_change_reviews": (
        "clinic_slug",
        "source_url",
        "status",
        "proposed_fields",
        "created_review",
    ),
    "submit_blocking_claim_reviews": ("clinic_slug", "clinic_name", "status", "claims"),
    "measure_source_snapshot_retention": ("clinic_name", "source_url", "snapshots", "prunable"),
    "measure_profile_completeness": (
        "clinic_name",
        "slug",
        "status",
        "pending_count",
        "pending_fields",
        "open_quality_reviews",
    ),
    "admin_digest": ("title", "review_type", "priority", "clinic_name", "clinic_slug"),
    "submit_source_shadow_reviews": (
        "clinic_slug",
        "clinic_name",
        "source_url",
        "status",
        "proposed_fields",
        "created_review",
    ),
    "check_production_health": ("name", "url", "status", "ok", "missing_markers", "error"),
}


def compact_item(item: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(item, dict) or not keys:
        return item
    return {key: item[key] for key in keys if key in item}


def compact_summary(name: str, summary: Any) -> Any:
    if not isinstance(summary, dict):
        return summary
    compact = dict(summary)
    compact.pop("admin_email", None)
    items = compact.get("items")
    if isinstance(items, list):
        compact["items_count"] = len(items)
        compact["sample_items"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in items[:3]
        ]
        compact.pop("items", None)
    evaluations = compact.get("evaluations")
    if isinstance(evaluations, list):
        compact["evaluations_count"] = len(evaluations)
        compact.pop("evaluations", None)
    top_sources = compact.get("top_sources")
    if isinstance(top_sources, list):
        compact["top_sources_count"] = len(top_sources)
        compact["sample_top_sources"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in top_sources[:3]
        ]
        compact.pop("top_sources", None)
    pending_profiles = compact.get("pending_profiles")
    if isinstance(pending_profiles, list):
        compact["pending_profiles_count"] = len(pending_profiles)
        compact["sample_pending_profiles"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in pending_profiles[:3]
        ]
        compact.pop("pending_profiles", None)
    open_reviews = compact.get("open_reviews")
    if isinstance(open_reviews, list):
        compact["open_reviews_count"] = len(open_reviews)
        compact["sample_open_reviews"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in open_reviews[:3]
        ]
        compact.pop("open_reviews", None)
    checks = compact.get("checks")
    if isinstance(checks, list):
        compact["checks_count"] = len(checks)
        compact["sample_checks"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in checks[:5]
        ]
        compact.pop("checks", None)
    return compact


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
    summary = try_parse_json(result.stdout)
    return {
        "name": name,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "duration_seconds": duration,
        "summary": compact_summary(name, summary),
        "stdout_tail": ""
        if result.returncode == 0 and summary is not None
        else result.stdout.strip()[-1200:],
        "stderr_tail": result.stderr.strip()[-1200:],
    }


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str], int]]:
    apply_flag = ["--apply"] if args.apply_safe else []
    steps = [
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
            "process_source_change_reviews",
            [
                "process_source_change_reviews.py",
                "--limit",
                str(args.source_change_limit),
                "--timeout",
                str(args.fetch_timeout),
                *apply_flag,
            ],
            max(90, args.source_change_limit * args.fetch_timeout + 30),
        ),
    ]
    if args.source_shadow_limit:
        source_shadow_args = [
            "submit_source_shadow_reviews.py",
            "--limit",
            str(args.source_shadow_limit),
            "--timeout",
            str(args.fetch_timeout),
            *apply_flag,
        ]
        if args.source_shadow_clinic_slug:
            source_shadow_args.extend(["--clinic-slug", args.source_shadow_clinic_slug])
        if args.source_shadow_replace_existing:
            source_shadow_args.append("--replace-existing")
        steps.append(
            (
                "submit_source_shadow_reviews",
                source_shadow_args,
                max(90, args.source_shadow_limit * args.fetch_timeout + 30),
            )
        )
    steps.extend([
        (
            "submit_blocking_claim_reviews",
            ["submit_blocking_claim_reviews.py", "--limit", str(args.blocking_claim_limit), *apply_flag],
            45,
        ),
        (
            "measure_source_snapshot_retention",
            [
                "measure_source_snapshot_retention.py",
                "--retention-days",
                str(args.snapshot_retention_days),
                "--keep-latest",
                str(args.snapshot_keep_latest),
                "--limit",
                str(args.snapshot_retention_limit),
                "--json",
            ],
            45,
        ),
        (
            "measure_profile_completeness",
            ["measure_profile_completeness.py", "--limit", str(args.profile_completeness_limit), "--json"],
            45,
        ),
        (
            "admin_digest",
            ["admin_digest.py", "--limit", str(args.digest_limit), "--json"],
            45,
        ),
        (
            "evaluate_claim_rules",
            ["evaluate_claim_rules.py", "--limit", str(args.claim_limit), "--json"],
            45,
        ),
    ])
    if args.strict_editorial:
        steps.append(
            (
                "check_operational_limits_strict",
                ["check_operational_limits.py", "--strict-editorial"],
                45,
            )
        )
    if args.production_health:
        steps.append(
            (
                "check_production_health",
                [
                    "check_production_health.py",
                    "--base-url",
                    args.production_base_url,
                    "--timeout",
                    str(args.production_timeout),
                    "--json",
                ],
                max(45, args.production_timeout * 6),
            )
        )
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-safe", action="store_true", help="Run safe internal writes; never publish or edit clinics.")
    parser.add_argument("--review-limit", type=int, default=100)
    parser.add_argument("--source-limit", type=int, default=40)
    parser.add_argument("--monitor-limit", type=int, default=40)
    parser.add_argument("--source-change-limit", type=int, default=10)
    parser.add_argument("--source-shadow-limit", type=int, default=0, help="Optional saved-source shadow extraction batch.")
    parser.add_argument("--source-shadow-clinic-slug", help="Limit optional saved-source batch to one clinic.")
    parser.add_argument("--source-shadow-replace-existing", action="store_true", help="Refresh matching open review cards.")
    parser.add_argument("--digest-limit", type=int, default=8)
    parser.add_argument("--claim-limit", type=int, default=100)
    parser.add_argument("--blocking-claim-limit", type=int, default=20)
    parser.add_argument("--snapshot-retention-days", type=int, default=180)
    parser.add_argument("--snapshot-keep-latest", type=int, default=3)
    parser.add_argument("--snapshot-retention-limit", type=int, default=8)
    parser.add_argument("--profile-completeness-limit", type=int, default=12)
    parser.add_argument("--fetch-timeout", type=int, default=12)
    parser.add_argument(
        "--production-health",
        action="store_true",
        help="Optionally check public production URLs; read-only and network-dependent.",
    )
    parser.add_argument(
        "--strict-editorial",
        action="store_true",
        help="Optionally fail on sensitive ranking/prize/comparison language that needs Daniel.",
    )
    parser.add_argument("--production-base-url", default="https://www.diuvita.com")
    parser.add_argument("--production-timeout", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if min(
        args.review_limit,
        args.source_limit,
        args.monitor_limit,
        args.source_change_limit,
        args.source_shadow_limit,
        args.digest_limit,
        args.claim_limit,
        args.blocking_claim_limit,
        args.snapshot_retention_days,
        args.snapshot_keep_latest,
        args.snapshot_retention_limit,
        args.profile_completeness_limit,
    ) < 0:
        raise SystemExit("limits must be zero or greater.")
    if min(
        args.review_limit,
        args.source_limit,
        args.monitor_limit,
        args.source_change_limit,
        args.digest_limit,
        args.claim_limit,
        args.blocking_claim_limit,
        args.snapshot_retention_days,
        args.snapshot_keep_latest,
        args.snapshot_retention_limit,
        args.profile_completeness_limit,
    ) < 1:
        raise SystemExit("limits must be at least 1.")
    if args.fetch_timeout < 3 or args.fetch_timeout > 60:
        raise SystemExit("--fetch-timeout must be between 3 and 60 seconds.")
    if args.production_timeout < 3 or args.production_timeout > 60:
        raise SystemExit("--production-timeout must be between 3 and 60 seconds.")

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
