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

from admin_digest import (
    SAFE_WRITE_REVIEW_BACKLOG_LIMIT,
    as_int,
    next_action_label,
    next_profile_action,
    next_source_action,
    source_coverage_status,
    top_pending_profile_field,
)


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
    "seed_visible_clinic_sources": (
        "clinic_name",
        "city",
        "status",
        "website",
        "source_url",
        "source_type",
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
    "measure_source_coverage": (
        "clinic_name",
        "slug",
        "status",
        "source_records",
        "hydrated_source_records",
        "total_claims",
        "claims_without_source",
        "blocking_claims",
    ),
    "measure_profile_completeness": (
        "clinic_name",
        "slug",
        "status",
        "pending_count",
        "pending_fields",
        "open_quality_reviews",
    ),
    "review_backlog_brief": (
        "clinic_name",
        "clinic_slug",
        "city",
        "clinic_status",
        "card_count",
        "blocking_claim_reviews",
        "enrichment_reviews",
        "source_change_reviews",
        "quality_reviews",
        "candidate_reviews",
        "max_priority",
        "oldest_created_at",
    ),
    "admin_digest": ("title", "review_type", "priority", "clinic_name", "clinic_slug"),
    "submit_source_shadow_reviews": (
        "clinic_slug",
        "clinic_name",
        "source_url",
        "status",
        "pending_count",
        "pending_fields",
        "proposed_fields",
        "created_review",
    ),
    "check_production_health": ("name", "url", "status", "ok", "missing_markers", "error"),
}


STEP_LABELS = {
    "capture_enrichment_review_claims": "captura de claims desde propuestas",
    "seed_visible_clinic_sources": "siembra de webs oficiales como fuentes",
    "hydrate_source_records": "hidratacion de fuentes",
    "monitor_source_changes": "vigilancia de cambios de fuentes",
    "process_source_change_reviews": "conversion de cambios en propuestas",
    "submit_source_shadow_reviews": "extraccion shadow desde fuentes guardadas",
    "submit_blocking_claim_reviews": "claims bloqueantes",
    "measure_source_snapshot_retention": "retencion de evidencias",
    "measure_source_coverage": "cobertura de fuentes",
    "measure_profile_completeness": "completitud de fichas",
    "review_backlog_brief": "atascos de bandeja",
    "admin_digest": "resumen interno",
    "evaluate_claim_rules": "reglas de publicacion",
    "check_operational_limits_strict": "limites operativos",
    "check_production_health": "salud de la web publica",
}

REVIEW_CARD_CREATING_STEPS = {
    "monitor_source_changes",
    "process_source_change_reviews",
    "submit_source_shadow_reviews",
    "submit_blocking_claim_reviews",
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
    source_work = compact.get("needs_source_work")
    if isinstance(source_work, list):
        compact["needs_source_work_count"] = len(source_work)
        compact["sample_needs_source_work"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in source_work[:3]
        ]
        compact.pop("needs_source_work", None)
    duplicate_enrichment = compact.get("duplicate_enrichment")
    if isinstance(duplicate_enrichment, list):
        compact["duplicate_enrichment_count"] = len(duplicate_enrichment)
        compact["sample_duplicate_enrichment"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in duplicate_enrichment[:3]
        ]
        compact.pop("duplicate_enrichment", None)
    clinic_workgroups = compact.get("clinic_workgroups")
    if isinstance(clinic_workgroups, list):
        compact["clinic_workgroups_count"] = len(clinic_workgroups)
        compact["sample_clinic_workgroups"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in clinic_workgroups[:3]
        ]
        compact.pop("clinic_workgroups", None)
    open_reviews = compact.get("open_reviews")
    if isinstance(open_reviews, list):
        compact["open_reviews_count"] = len(open_reviews)
        compact["sample_open_reviews"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in open_reviews[:3]
        ]
        compact.pop("open_reviews", None)
    backlog_quality = compact.get("review_backlog_quality")
    if isinstance(backlog_quality, dict):
        compact["review_backlog_quality"] = {
            "duplicate_enrichment_clinics": backlog_quality.get("duplicate_enrichment_clinics", 0),
            "duplicate_enrichment_reviews": backlog_quality.get("duplicate_enrichment_reviews", 0),
        }
    review_examples = compact.get("review_examples_by_type")
    if isinstance(review_examples, list):
        compact["review_examples_by_type_count"] = len(review_examples)
        compact["sample_review_examples_by_type"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in review_examples[:5]
        ]
        compact.pop("review_examples_by_type", None)
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


def skipped_step(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": True,
        "skipped": True,
        "returncode": 0,
        "duration_seconds": 0,
        "summary": {"status": "skipped", "reason": reason},
        "stdout_tail": "",
        "stderr_tail": "",
    }


def open_review_count_from_digest(digest: dict[str, Any]) -> int:
    summary = digest.get("summary") if isinstance(digest.get("summary"), dict) else {}
    reviews = summary.get("reviews") if isinstance(summary.get("reviews"), dict) else {}
    return as_int(reviews.get("open"))


def step_label(name: str) -> str:
    return STEP_LABELS.get(name, name.replace("_", " "))


def first_failed_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if not step.get("ok"):
            return step
    return None


def find_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for step in steps:
        if step.get("name") == name:
            return step
    return None


def safe_step_summary(step: dict[str, Any] | None) -> dict[str, Any]:
    if not step:
        return {}
    summary = step.get("summary")
    return summary if isinstance(summary, dict) else {}


def build_cycle_brief(output: dict[str, Any]) -> dict[str, Any]:
    steps = [step for step in output.get("steps") or [] if isinstance(step, dict)]
    failed_step = first_failed_step(steps)
    admin_digest = safe_step_summary(find_step(steps, "admin_digest"))
    admin_summary = admin_digest.get("summary") if isinstance(admin_digest.get("summary"), dict) else {}
    reviews = admin_summary.get("reviews") if isinstance(admin_summary.get("reviews"), dict) else {}
    jobs = admin_summary.get("jobs") if isinstance(admin_summary.get("jobs"), dict) else {}
    automation = admin_summary.get("automation") if isinstance(admin_summary.get("automation"), dict) else {}
    failed_jobs = as_int(jobs.get("failed")) + as_int(jobs.get("dead_letter"))
    open_reviews = as_int(reviews.get("open"))
    mode = str(output.get("mode") or "dry_run")
    mode_label = "solo lectura" if mode == "dry_run" else "cambios internos seguros"
    completed_steps = len([step for step in steps if step.get("ok") and not step.get("skipped")])
    skipped_steps = len([step for step in steps if step.get("skipped")])
    total_steps = len(steps)

    if failed_step:
        failed_name = str(failed_step.get("name") or "")
        if failed_name == "check_operational_limits_strict":
            status = "needs_daniel"
            attention = "Hay una decision de limites operativos para Daniel antes de seguir por esa via."
        elif failed_name == "check_production_health":
            status = "attention"
            attention = "La web publica no paso una comprobacion de salud; conviene revisarla antes de aceptar cambios nuevos."
        else:
            status = "attention"
            attention = "Hay un fallo tecnico en el ciclo; revisar el paso detenido antes de aceptar nuevas fichas."
        headline = f"Ciclo detenido en {step_label(failed_name)}."
    else:
        if failed_jobs:
            status = "attention"
            attention = "Hay fallos tecnicos abiertos en la bandeja interna."
        elif skipped_steps:
            status = "attention"
            attention = "Se omitieron pasos que podian crear mas tarjetas porque la bandeja ya esta cargada."
        else:
            status = "ok"
            attention = ""
        headline = f"Ciclo completado en modo {mode_label}."

    production_step = find_step(steps, "check_production_health")
    production_summary = safe_step_summary(production_step)
    if not production_step:
        production_health = "no comprobada en este ciclo"
    elif production_step.get("ok") and production_summary.get("ok"):
        production_health = "OK"
    else:
        production_health = "revisar"

    if admin_digest:
        next_action = next_action_label(admin_digest)
        profile_gap = top_pending_profile_field(admin_digest)
        profile_next = next_profile_action(admin_digest)
        source_gap = source_coverage_status(admin_digest)
        source_next = next_source_action(admin_digest)
    elif failed_step:
        next_action = "Revisar el paso detenido"
        profile_gap = "no medido"
        profile_next = "no medida"
        source_gap = "no medida"
        source_next = "no medida"
    else:
        next_action = "Sin accion urgente"
        profile_gap = "no medido"
        profile_next = "no medida"
        source_gap = "no medida"
        source_next = "no medida"

    auto_publish = bool(automation.get("auto_publish_enabled"))
    shadow_mode = bool(automation.get("shadow_mode_active"))
    publication_guard = (
        "Auto-publicacion activa; revisar con especial cuidado antes de ampliar reglas."
        if auto_publish
        else "Auto-publicacion apagada; crear borrador no publica."
    )

    return {
        "status": status,
        "headline": headline,
        "mode": mode_label,
        "steps": f"{completed_steps}/{total_steps} pasos OK",
        "skipped_steps": skipped_steps,
        "next_action": next_action,
        "open_reviews": open_reviews,
        "failed_jobs": failed_jobs,
        "profile_gap": profile_gap,
        "profile_next": profile_next,
        "source_gap": source_gap,
        "source_next": source_next,
        "publication_guard": publication_guard,
        "shadow_mode": "activo" if shadow_mode else "inactivo",
        "production_health": production_health,
        "attention": attention,
    }


def format_cycle_brief(brief: dict[str, Any]) -> str:
    lines = [
        "# Diuvita: resumen CTO automatico",
        "",
        f"- Estado: {brief.get('headline')}",
        f"- Pasos: {brief.get('steps')}",
        f"- Que mirar primero: {brief.get('next_action')}.",
        f"- Revisiones abiertas: {brief.get('open_reviews')}",
        f"- Campo mas pendiente: {brief.get('profile_gap')}.",
        f"- Siguiente ficha: {brief.get('profile_next')}.",
        f"- Cobertura fuentes: {brief.get('source_gap')}.",
        f"- Siguiente fuente: {brief.get('source_next')}.",
        f"- Publicacion: {brief.get('publication_guard')}",
        f"- Modo sombra: {brief.get('shadow_mode')}.",
        f"- Web publica: {brief.get('production_health')}.",
    ]
    if as_int(brief.get("skipped_steps")):
        lines.append(f"- Pasos omitidos: {brief.get('skipped_steps')}")
    attention = str(brief.get("attention") or "").strip()
    if attention:
        lines.append(f"- Atencion: {attention}")
    return "\n".join(lines) + "\n"


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str], int]]:
    apply_flag = ["--apply"] if args.apply_safe else []
    steps = [
        (
            "capture_enrichment_review_claims",
            ["capture_enrichment_review_claims.py", "--limit", str(args.review_limit), *apply_flag],
            90,
        ),
        (
            "seed_visible_clinic_sources",
            ["seed_visible_clinic_sources.py", "--limit", str(args.seed_source_limit), "--json", *apply_flag],
            45,
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
            "measure_source_coverage",
            ["measure_source_coverage.py", "--limit", str(args.source_coverage_limit), "--json"],
            45,
        ),
        (
            "measure_profile_completeness",
            ["measure_profile_completeness.py", "--limit", str(args.profile_completeness_limit), "--json"],
            45,
        ),
        (
            "review_backlog_brief",
            ["review_backlog_brief.py", "--limit", str(args.backlog_brief_limit), "--json"],
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
    parser.add_argument("--seed-source-limit", type=int, default=20)
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
    parser.add_argument("--source-coverage-limit", type=int, default=12)
    parser.add_argument("--profile-completeness-limit", type=int, default=12)
    parser.add_argument("--backlog-brief-limit", type=int, default=8)
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
    parser.add_argument(
        "--plain-brief",
        action="store_true",
        help="Print only Daniel's plain-language cycle brief instead of the technical JSON.",
    )
    parser.add_argument(
        "--max-open-reviews-for-safe-writes",
        type=int,
        default=SAFE_WRITE_REVIEW_BACKLOG_LIMIT,
        help="In apply-safe mode, skip review-card writing steps once open reviews reach this count. Use 0 to disable.",
    )
    parser.add_argument("--production-base-url", default="https://www.diuvita.com")
    parser.add_argument("--production-timeout", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if min(
        args.review_limit,
        args.seed_source_limit,
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
        args.max_open_reviews_for_safe_writes,
    ) < 0:
        raise SystemExit("limits must be zero or greater.")
    if min(
        args.review_limit,
        args.seed_source_limit,
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
    review_card_writes_allowed = True
    backlog_guard_reason = ""
    if args.apply_safe and args.max_open_reviews_for_safe_writes:
        preflight = run_step(
            "preflight_review_backlog",
            ["admin_digest.py", "--limit", "1", "--json"],
            45,
        )
        steps.append(preflight)
        if not preflight["ok"]:
            output = {
                "mode": "apply_safe",
                "ok": False,
                "steps": steps,
            }
            output["daniel_brief"] = build_cycle_brief(output)
            if args.plain_brief:
                print(format_cycle_brief(output["daniel_brief"]), end="")
            else:
                print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1
        open_reviews = open_review_count_from_digest(safe_step_summary(preflight))
        if open_reviews >= args.max_open_reviews_for_safe_writes:
            review_card_writes_allowed = False
            backlog_guard_reason = (
                f"{open_reviews} revisiones abiertas; limite seguro "
                f"{args.max_open_reviews_for_safe_writes}."
            )

    for name, command_args, timeout in build_steps(args):
        if args.apply_safe and not review_card_writes_allowed and name in REVIEW_CARD_CREATING_STEPS:
            steps.append(skipped_step(name, backlog_guard_reason))
            continue
        step = run_step(name, command_args, timeout)
        steps.append(step)
        if not step["ok"]:
            break

    output = {
        "mode": "apply_safe" if args.apply_safe else "dry_run",
        "ok": all(step["ok"] for step in steps),
        "steps": steps,
    }
    output["daniel_brief"] = build_cycle_brief(output)
    if args.plain_brief:
        print(format_cycle_brief(output["daniel_brief"]), end="")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
