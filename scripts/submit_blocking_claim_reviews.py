#!/usr/bin/env python3
"""Create internal review cards for blocking field claims.

The tool is safe by default. It reads rejected/conflict/source-less claims and
can create or refresh clinic_quality_audit review cards. It never edits clinic
profiles and never publishes public pages.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)


TOOL_NAME = "diuvita-blocking-claim-reviewer"
TOOL_VERSION = "2026-08-30"


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def priority_for_claims(claims: list[dict[str, Any]]) -> int:
    statuses = {str(claim.get("blocker_status") or claim.get("verification_status") or "") for claim in claims}
    if "conflict" in statuses:
        return 95
    if "rejected" in statuses:
        return 85
    if "without_source" in statuses:
        return 75
    return 60


def issue_label(claim: dict[str, Any]) -> str:
    field_path = str(claim.get("field_path") or "campo")
    status = str(claim.get("blocker_status") or claim.get("verification_status") or "")
    if status == "conflict":
        return "Claim en conflicto: " + field_path
    if status == "rejected":
        return "Claim rechazado: " + field_path
    if status == "without_source":
        return "Claim sin fuente: " + field_path
    return "Claim pendiente: " + field_path


def review_payload(group: dict[str, Any]) -> dict[str, Any]:
    claims = [claim for claim in group.get("claims") or [] if isinstance(claim, dict)]
    return {
        "mode": "shadow",
        "quality_context": "blocking_claims",
        "reviewer": TOOL_NAME,
        "reviewer_version": TOOL_VERSION,
        "clinic_id": group.get("clinic_id"),
        "clinic_slug": group.get("clinic_slug"),
        "clinic_name": group.get("clinic_name"),
        "clinic_city": group.get("clinic_city"),
        "clinic_country": group.get("clinic_country"),
        "website": group.get("website"),
        "issues": [
            {
                "code": "blocking_claim",
                "label": issue_label(claim),
                "field_path": claim.get("field_path"),
                "verification_status": claim.get("verification_status"),
                "blocker_status": claim.get("blocker_status"),
                "claim_id": claim.get("claim_id"),
                "source_url": claim.get("source_url"),
            }
            for claim in claims
        ],
        "blocked_claims": claims,
        "warnings": [
            "Revisar claims bloqueantes antes de relajar reglas o activar cualquier auto-publicacion."
        ],
    }


def load_blocking_claim_groups(limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    sql = f"""
with blocked as (
  select
    fc.id as claim_id,
    fc.clinic_id,
    fc.field_path,
    fc.verification_status,
    case
      when fc.verification_status in ('conflict', 'rejected') then fc.verification_status
      when fc.source_record_id is null then 'without_source'
      else fc.verification_status
    end as blocker_status,
    fc.confidence,
    fc.source_record_id,
    fc.created_at,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city as clinic_city,
    c.country as clinic_country,
    c.website,
    sr.source_url,
    case
      when fc.verification_status = 'conflict' then 95
      when fc.verification_status = 'rejected' then 85
      when fc.source_record_id is null then 75
      else 60
    end as priority
  from public.field_claims fc
  join public.clinics c on c.id = fc.clinic_id
  left join public.source_records sr on sr.id = fc.source_record_id
  where fc.verification_status in ('conflict', 'rejected')
     or fc.source_record_id is null
),
grouped as (
  select
    clinic_id,
    clinic_slug,
    clinic_name,
    clinic_city,
    clinic_country,
    website,
    max(priority) as priority,
    max(created_at) as latest_created_at,
    jsonb_agg(
      jsonb_build_object(
        'claim_id', claim_id,
        'field_path', field_path,
        'verification_status', verification_status,
        'blocker_status', blocker_status,
        'confidence', confidence,
        'source_record_id', source_record_id,
        'source_url', source_url,
        'created_at', created_at
      )
      order by priority desc, created_at desc
    ) as claims
  from blocked
  group by clinic_id, clinic_slug, clinic_name, clinic_city, clinic_country, website
  order by max(priority) desc, max(created_at) desc
  limit {int(limit)}
)
select coalesce(
  jsonb_agg(
    jsonb_build_object(
      'clinic_id', clinic_id,
      'clinic_slug', clinic_slug,
      'clinic_name', clinic_name,
      'clinic_city', clinic_city,
      'clinic_country', clinic_country,
      'website', website,
      'priority', priority,
      'latest_created_at', latest_created_at,
      'claims', claims
    )
    order by priority desc, latest_created_at desc
  ),
  '[]'::jsonb
)
from grouped;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def create_review_sql(group: dict[str, Any], admin_email: str) -> str:
    claims = [claim for claim in group.get("claims") or [] if isinstance(claim, dict)]
    priority = priority_for_claims(claims) or as_int(group.get("priority")) or 75
    title = "Revisar claims bloqueantes: " + str(group.get("clinic_name") or group.get("clinic_slug") or "clinica")
    payload_sql = sql_literal(json.dumps(review_payload(group), ensure_ascii=False)) + "::jsonb"
    return f"""
with target as (
  select id
  from public.clinics
  where id = {sql_literal(group.get("clinic_id"))}::uuid
),
existing as (
  select rq.id
  from public.review_queue rq
  join target t on t.id = rq.clinic_id
  where rq.review_type = 'clinic_quality_audit'
    and rq.status = 'open'
    and rq.payload ->> 'quality_context' = 'blocking_claims'
  limit 1
),
updated as (
  update public.review_queue rq
  set
    title = {sql_literal(title)},
    field_path = 'field_claims',
    priority = greatest(rq.priority, {priority}),
    payload = jsonb_strip_nulls({payload_sql} || jsonb_build_object('refreshed_at', now())),
    assigned_to = {sql_literal(admin_email)}
  from existing e
  where rq.id = e.id
  returning 'updated' as status, rq.id, rq.title
),
inserted as (
  insert into public.review_queue (
    clinic_id,
    review_type,
    title,
    field_path,
    priority,
    status,
    payload,
    assigned_to
  )
  select
    t.id,
    'clinic_quality_audit',
    {sql_literal(title)},
    'field_claims',
    {priority},
    'open',
    jsonb_strip_nulls({payload_sql}),
    {sql_literal(admin_email)}
  from target t
  where not exists (select 1 from updated)
  returning 'inserted' as status, id, title
),
resolved as (
  select * from updated
  union all
  select * from inserted
)
select coalesce(jsonb_agg(to_jsonb(resolved.*)), '[]'::jsonb)
from resolved;
"""


def create_review(group: dict[str, Any], admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    rows = json.loads(run_psql(create_review_sql(group, admin_email), local_env) or "[]")
    if not rows:
        return {"status": "missing", "clinic_slug": group.get("clinic_slug")}
    row = rows[0]
    row["clinic_slug"] = group.get("clinic_slug")
    row["claims"] = len(group.get("claims") or [])
    return row


def record_event(results: list[dict[str, Any]], admin_email: str, local_env: dict[str, str]) -> None:
    inserted = [item.get("clinic_slug") for item in results if item.get("status") == "inserted"]
    updated = [item.get("clinic_slug") for item in results if item.get("status") == "updated"]
    payload = json.dumps(
        {
            "reviewer": TOOL_NAME,
            "reviewer_version": TOOL_VERSION,
            "inserted": inserted,
            "updated": updated,
            "total": len(results),
        },
        ensure_ascii=False,
    )
    sql = f"""
insert into public.change_events (
  event_name,
  actor_type,
  actor_id,
  entity_type,
  payload
)
values (
  'blocking_claim_reviews_created',
  'admin',
  {sql_literal(admin_email)},
  'review_queue',
  {sql_literal(payload)}::jsonb
);
"""
    run_psql(sql, local_env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--admin-email", help="Admin email used for assignment/audit.")
    parser.add_argument("--apply", action="store_true", help="Create or refresh internal review cards.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    groups = load_blocking_claim_groups(args.limit, local_env)
    if not args.apply:
        print(json.dumps({
            "mode": "dry_run",
            "groups_seen": len(groups),
            "items": [
                {
                    "clinic_slug": group.get("clinic_slug"),
                    "clinic_name": group.get("clinic_name"),
                    "claims": len(group.get("claims") or []),
                    "priority": priority_for_claims(group.get("claims") or []),
                }
                for group in groups
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    results = [create_review(group, admin_email, local_env) for group in groups]
    if results:
        record_event(results, admin_email, local_env)
    print(json.dumps({
        "mode": "apply",
        "groups_seen": len(groups),
        "inserted": sum(1 for item in results if item.get("status") == "inserted"),
        "updated": sum(1 for item in results if item.get("status") == "updated"),
        "missing": sum(1 for item in results if item.get("status") == "missing"),
        "items": results,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
