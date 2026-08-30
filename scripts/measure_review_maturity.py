#!/usr/bin/env python3
"""Read-only maturity measurement before any Diuvita auto-publish expansion."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from admin_digest import as_int, format_review_type, parse_timestamp
from submit_blocking_claim_reviews import NON_NOISY_BLOCKING_CLAIM_SQL
from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)


DEFAULT_REVIEW_TARGET = 200


def percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{round((numerator / denominator) * 100)}%"


def load_measurement(admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
summary as (
  select public.admin_dashboard_summary() as data
  from claims
),
reviews_by_type as (
  select coalesce(jsonb_agg(to_jsonb(grouped) order by grouped.review_type), '[]'::jsonb) as data
  from (
    select
      review_type,
      count(*) as total,
      count(*) filter (where status = 'open') as open,
      count(*) filter (where status = 'resolved') as resolved,
      count(*) filter (where status = 'dismissed') as dismissed,
      min(created_at) filter (where status = 'open') as oldest_open_at,
      max(resolved_at) filter (where status in ('resolved', 'dismissed')) as last_closed_at
    from public.review_queue
    group by review_type
  ) grouped
),
claims_by_status as (
  select coalesce(jsonb_agg(to_jsonb(grouped) order by grouped.verification_status), '[]'::jsonb) as data
  from (
    select
      verification_status,
      count(*) as total
    from public.field_claims
    group by verification_status
  ) grouped
),
claims_by_field as (
  select coalesce(jsonb_agg(to_jsonb(grouped) order by grouped.total desc, grouped.field_path), '[]'::jsonb) as data
  from (
    select
      field_path,
      count(*) as total,
      count(*) filter (where verification_status = 'accepted') as accepted,
      count(*) filter (where verification_status in ('proposed', 'review', 'conflict')) as needs_review,
      count(*) filter (where verification_status = 'rejected') as rejected
    from public.field_claims
    group by field_path
    limit 30
  ) grouped
),
blocked_claims as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.severity desc, items.created_at desc), '[]'::jsonb) as data
  from (
    select
      fc.id,
      fc.field_path,
      fc.verification_status,
      fc.confidence,
      fc.source_record_id,
      fc.created_at,
      c.slug as clinic_slug,
      c.display_name as clinic_name,
      sr.source_url,
      case
        when fc.verification_status = 'conflict' then 3
        when fc.verification_status = 'rejected' then 2
        when fc.source_record_id is null then 1
        else 0
      end as severity
    from public.field_claims fc
    left join public.clinics c on c.id = fc.clinic_id
    left join public.source_records sr on sr.id = fc.source_record_id
    where (
        fc.verification_status = 'conflict'
        or fc.source_record_id is null
      )
      and {NON_NOISY_BLOCKING_CLAIM_SQL}
    order by severity desc, fc.created_at desc
    limit 20
  ) items
),
source_coverage as (
  select jsonb_build_object(
    'source_records', (select count(*) from public.source_records),
    'source_snapshots', (select count(*) from public.source_snapshots),
    'claims_with_source', count(*) filter (where source_record_id is not null),
    'claims_without_source', count(*) filter (where source_record_id is null)
  ) as data
  from public.field_claims
),
jobs_7d as (
  select jsonb_build_object(
    'total', count(*),
    'completed', count(*) filter (where status = 'completed'),
    'queued', count(*) filter (where status = 'queued'),
    'running', count(*) filter (where status = 'running'),
    'failed', count(*) filter (where status in ('failed', 'dead_letter'))
  ) as data
  from public.agent_jobs
  where created_at >= now() - interval '7 days'
)
select jsonb_build_object(
  'summary', (select data from summary),
  'reviews_by_type', (select data from reviews_by_type),
  'claims_by_status', (select data from claims_by_status),
  'claims_by_field', (select data from claims_by_field),
  'blocked_claims', (select data from blocked_claims),
  'source_coverage', (select data from source_coverage),
  'jobs_7d', (select data from jobs_7d),
  'generated_at', now()
);
"""
    return json.loads(run_psql(sql, local_env))


def keyed(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key) or ""): row for row in rows if isinstance(row, dict)}


def review_target(measurement: dict[str, Any], requested_target: int | None) -> int:
    if requested_target:
        return requested_target
    summary = measurement.get("summary") or {}
    automation = summary.get("automation") or {}
    return as_int(automation.get("shadow_review_target")) or DEFAULT_REVIEW_TARGET


def confidence_label(value: Any) -> str:
    try:
        return f"{round(float(value or 0) * 100)}%"
    except (TypeError, ValueError):
        return "-"


def maturity_status(measurement: dict[str, Any], target: int) -> dict[str, Any]:
    reviews = keyed(measurement.get("reviews_by_type") or [], "review_type")
    candidate = reviews.get("candidate_clinic") or {}
    completed_candidates = as_int(candidate.get("resolved")) + as_int(candidate.get("dismissed"))
    claims_status = keyed(measurement.get("claims_by_status") or [], "verification_status")
    conflicts = as_int((claims_status.get("conflict") or {}).get("total"))
    rejected = as_int((claims_status.get("rejected") or {}).get("total"))
    jobs = measurement.get("jobs_7d") or {}
    failed_jobs = as_int(jobs.get("failed"))

    blockers = []
    if completed_candidates < target:
        blockers.append(f"Human review sample is still small: {completed_candidates}/{target} candidate decisions.")
    if conflicts:
        blockers.append(f"{conflicts} field claims are marked as conflicts.")
    if rejected:
        blockers.append(f"{rejected} field claims were rejected and should be reviewed before loosening rules.")
    if failed_jobs:
        blockers.append(f"{failed_jobs} jobs failed or reached dead-letter in the last 7 days.")

    return {
        "ready_for_low_risk_autopublish": not blockers,
        "completed_candidate_reviews": completed_candidates,
        "target_candidate_reviews": target,
        "blockers": blockers,
    }


def format_measurement(measurement: dict[str, Any], target: int) -> str:
    summary = measurement.get("summary") or {}
    clinics = summary.get("clinics") or {}
    reviews = measurement.get("reviews_by_type") or []
    claims_status = measurement.get("claims_by_status") or []
    claims_field = measurement.get("claims_by_field") or []
    blocked_claims = measurement.get("blocked_claims") or []
    source_coverage = measurement.get("source_coverage") or {}
    jobs = measurement.get("jobs_7d") or {}
    status = maturity_status(measurement, target)

    lines = [
        "# Diuvita review maturity",
        "",
        f"Generated: {parse_timestamp(measurement.get('generated_at'))}",
        "",
        "## Decision",
        "- Low-risk auto-publish readiness: "
        + ("ready" if status["ready_for_low_risk_autopublish"] else "not ready"),
        f"- Candidate review sample: {status['completed_candidate_reviews']}/{status['target_candidate_reviews']}",
    ]
    for blocker in status["blockers"]:
        lines.append(f"- Blocker: {blocker}")

    lines.extend([
        "",
        "## Clinic inventory",
        f"- Total: {as_int(clinics.get('total'))}",
        f"- Published: {as_int(clinics.get('published'))}",
        f"- Preliminary: {as_int(clinics.get('preliminary'))}",
        f"- Draft: {as_int(clinics.get('draft'))}",
        "",
        "## Human review outcomes",
    ])
    if reviews:
        for row in reviews:
            total = as_int(row.get("total"))
            closed = as_int(row.get("resolved")) + as_int(row.get("dismissed"))
            label = format_review_type(str(row.get("review_type") or ""))
            lines.append(
                f"- {label}: {closed}/{total} closed ({percent(closed, total)}), "
                f"{as_int(row.get('open'))} open"
            )
    else:
        lines.append("- No review history yet.")

    lines.extend([
        "",
        "## Field claims",
    ])
    if claims_status:
        for row in claims_status:
            lines.append(f"- {row.get('verification_status')}: {as_int(row.get('total'))}")
    else:
        lines.append("- No field claims recorded.")

    if blocked_claims:
        lines.extend(["", "## Blocking claims"])
        for row in blocked_claims[:10]:
            clinic = row.get("clinic_name") or row.get("clinic_slug") or "sin clinica"
            verification = row.get("verification_status") or "sin fuente"
            source = "con fuente" if row.get("source_record_id") else "sin fuente"
            lines.append(
                f"- {clinic} | {row.get('field_path')}: {verification}, "
                f"{confidence_label(row.get('confidence'))}, {source}"
            )

    lines.extend([
        "",
        "## Source coverage",
        f"- Source records: {as_int(source_coverage.get('source_records'))}",
        f"- Source snapshots: {as_int(source_coverage.get('source_snapshots'))}",
        f"- Claims with source: {as_int(source_coverage.get('claims_with_source'))}",
        f"- Claims without source: {as_int(source_coverage.get('claims_without_source'))}",
    ])

    if claims_field:
        lines.extend(["", "## Largest claim groups"])
        for row in claims_field[:10]:
            lines.append(
                f"- {row.get('field_path')}: {as_int(row.get('total'))} total, "
                f"{as_int(row.get('needs_review'))} need review"
            )

    lines.extend([
        "",
        "## Jobs in the last 7 days",
        f"- Total: {as_int(jobs.get('total'))}",
        f"- Completed: {as_int(jobs.get('completed'))}",
        f"- Queued: {as_int(jobs.get('queued'))}",
        f"- Running: {as_int(jobs.get('running'))}",
        f"- Failed/dead-letter: {as_int(jobs.get('failed'))}",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used for protected read-only queries.")
    parser.add_argument("--input-json", type=Path, help="Format a saved measurement instead of querying Supabase.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    parser.add_argument("--target", type=int, help="Human candidate-review target before auto-publish readiness.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input_json:
        measurement = json.loads(args.input_json.read_text(encoding="utf-8"))
    else:
        local_env = load_env_file()
        admin_email = args.admin_email or get_default_admin_email(local_env)
        measurement = load_measurement(admin_email, local_env)
    target = review_target(measurement, args.target)
    if args.json:
        print(json.dumps(measurement, ensure_ascii=False, indent=2))
    else:
        print(format_measurement(measurement, target), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
