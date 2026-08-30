#!/usr/bin/env python3
"""Capture clinic enrichment review payloads as source records and field claims.

This is an internal, shadow-mode step. It stores evidence and proposed claims,
but never changes a public clinic profile.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)
from submit_blocking_claim_reviews import is_noisy_title_identity_claim


AGENT_NAME = "vitalarga-profile-enrichment"
AGENT_VERSION = "2026-08-30"

FIELD_MAP = {
    "display_name": "profile.name",
    "name": "profile.name",
    "web": "contact.website",
    "website": "contact.website",
    "country": "location.country",
    "city": "location.city",
    "region": "location.region",
    "address": "location.address",
    "summary": "summary",
    "services": "services.list",
    "specialties": "specialties.list",
    "unidades": "units.list",
    "profesionales": "professionals.published",
    "professionals": "professionals.published",
    "tech": "technologies.list",
    "email": "contact.email",
    "telefono": "contact.phone",
    "phone": "contact.phone",
    "instagram": "contact.instagram",
}

VERDICT_STATUS = {
    "accepted": "review",
    "review": "review",
    "partial": "review",
    "conflict": "conflict",
    "stale": "stale",
    "rejected": "rejected",
}


def confidence(value: Any, default: float = 0.65) -> float:
    try:
        clean = float(value)
    except (TypeError, ValueError):
        clean = default
    return max(0.0, min(1.0, clean))


def source_urls(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("source_urls") or payload.get("sources") or payload.get("source_url")
    if not isinstance(raw, list):
        raw = [raw] if raw else []
    urls = []
    seen = set()
    for item in raw:
        url = str(item or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def decision_by_field(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for decision in payload.get("rule_decisions") or []:
        if isinstance(decision, dict) and decision.get("field_path"):
            result[str(decision["field_path"])] = decision
    return result


def normalized_status(raw_status: Any) -> str:
    return VERDICT_STATUS.get(str(raw_status or "").lower(), "review")


def claim_key(claim: dict[str, Any]) -> tuple[str, str]:
    return (
        str(claim.get("field_path") or ""),
        json.dumps(claim.get("value"), ensure_ascii=False, sort_keys=True),
    )


def add_claim(claims: list[dict[str, Any]], seen: set[tuple[str, str]], claim: dict[str, Any]) -> None:
    field_path = str(claim.get("field_path") or "").strip()
    if not field_path or claim.get("value") in (None, "", [], {}):
        return
    clean = {
        "field_path": field_path,
        "value": claim.get("value"),
        "confidence": confidence(claim.get("confidence")),
        "verification_status": normalized_status(claim.get("verification_status")),
        "agent_name": claim.get("agent_name") or AGENT_NAME,
        "agent_version": claim.get("agent_version") or AGENT_VERSION,
    }
    key = claim_key(clean)
    if key in seen:
        return
    seen.add(key)
    claims.append(clean)


def field_claims(payload: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    decisions = decision_by_field(payload)

    for raw in payload.get("field_claims") or []:
        if not isinstance(raw, dict):
            continue
        field_path = str(raw.get("field_path") or "").strip()
        decision = decisions.get(field_path) or {}
        if decision.get("action") == "reject" and raw.get("verifier_verdict") != "rejected":
            status = "rejected"
        else:
            status = normalized_status(raw.get("verifier_verdict") or raw.get("verification_status"))
        candidate_claim = {
            "field_path": field_path,
            "value": raw.get("value"),
            "confidence": raw.get("confidence"),
            "verification_status": status,
            "agent_name": raw.get("agent_name") or AGENT_NAME,
            "agent_version": raw.get("agent_version") or AGENT_VERSION,
        }
        if is_noisy_title_identity_claim(candidate_claim):
            continue
        add_claim(
            claims,
            seen,
            candidate_claim,
        )

    proposed = payload.get("proposed_fields") or {}
    if isinstance(proposed, dict):
        for source_key, value in proposed.items():
            add_claim(
                claims,
                seen,
                {
                    "field_path": FIELD_MAP.get(str(source_key), str(source_key)),
                    "value": value,
                    "confidence": 0.65,
                    "verification_status": "review",
                    "agent_name": AGENT_NAME,
                    "agent_version": AGENT_VERSION,
                },
            )

    return claims


def values_source_sql(urls: list[str]) -> str:
    if not urls:
        return "select null::text as source_url where false"
    return "values " + ", ".join(f"({sql_literal(url)})" for url in urls)


def values_claim_sql(claims: list[dict[str, Any]]) -> str:
    if not claims:
        return """
select
  null::text as field_path,
  null::jsonb as value,
  null::numeric as confidence,
  null::text as verification_status,
  null::text as agent_name,
  null::text as agent_version
where false
"""
    rows = []
    for claim in claims:
        rows.append(
            "("
            + ", ".join(
                [
                    sql_literal(claim["field_path"]),
                    sql_literal(json.dumps(claim["value"], ensure_ascii=False)) + "::jsonb",
                    f"{confidence(claim.get('confidence')):.4f}",
                    sql_literal(claim["verification_status"]),
                    sql_literal(claim["agent_name"]),
                    sql_literal(claim["agent_version"]),
                ]
            )
            + ")"
        )
    return "values " + ", ".join(rows)


def fetch_reviews(review_id: str | None, include_captured: bool, limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    captured_filter = "true" if include_captured else "coalesce((payload ->> 'field_claims_captured')::boolean, false) = false"
    review_filter = f"and id = {sql_literal(review_id)}::uuid" if review_id else ""
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.created_at asc), '[]'::jsonb)
from (
  select
    id,
    clinic_id,
    title,
    payload,
    created_at
  from public.review_queue
  where status = 'open'
    and review_type = 'clinic_profile_enrichment'
    and {captured_filter}
    {review_filter}
  order by created_at asc
  limit {int(limit)}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def capture_review(row: dict[str, Any], admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    urls = source_urls(payload)
    claims = field_claims(payload)
    if not row.get("clinic_id"):
        return {
            "review_id": row.get("id"),
            "status": "missing_clinic",
            "source_urls": len(urls),
            "field_claims": len(claims),
        }

    sql = f"""
with source_input(source_url) as (
  {values_source_sql(urls)}
),
inserted_sources as (
  insert into public.source_records (
    clinic_id,
    entity_type,
    entity_id,
    source_url,
    source_type,
    metadata
  )
  select
    {sql_literal(row["clinic_id"])}::uuid,
    'clinic',
    {sql_literal(row["clinic_id"])}::uuid,
    source_url,
    'website',
    jsonb_build_object(
      'review_id', {sql_literal(row["id"])},
      'capture_mode', 'review_payload',
      'captured_by', {sql_literal(admin_email)}
    )
  from source_input
  where not exists (
    select 1
    from public.source_records sr
    where sr.clinic_id = {sql_literal(row["clinic_id"])}::uuid
      and sr.entity_type = 'clinic'
      and sr.source_url = source_input.source_url
  )
  returning id, source_url
),
available_sources as (
  select id, source_url from inserted_sources
  union all
  select sr.id, sr.source_url
  from public.source_records sr
  join source_input on source_input.source_url = sr.source_url
  where sr.clinic_id = {sql_literal(row["clinic_id"])}::uuid
    and sr.entity_type = 'clinic'
),
primary_source as (
  select id
  from available_sources
  order by source_url asc
  limit 1
),
claim_input(field_path, value, confidence, verification_status, agent_name, agent_version) as (
  {values_claim_sql(claims)}
),
inserted_claims as (
  insert into public.field_claims (
    clinic_id,
    entity_type,
    entity_id,
    field_path,
    value,
    normalized_value,
    source_record_id,
    agent_name,
    agent_version,
    confidence,
    verification_status,
    human_locked
  )
  select
    {sql_literal(row["clinic_id"])}::uuid,
    'clinic',
    {sql_literal(row["clinic_id"])}::uuid,
    claim_input.field_path,
    claim_input.value,
    claim_input.value,
    (select id from primary_source),
    claim_input.agent_name,
    claim_input.agent_version,
    claim_input.confidence,
    claim_input.verification_status,
    exists (
      select 1
      from public.human_overrides ho
      where ho.clinic_id = {sql_literal(row["clinic_id"])}::uuid
        and ho.entity_type = 'clinic'
        and ho.field_path = claim_input.field_path
        and ho.locked = true
    )
  from claim_input
  where not exists (
    select 1
    from public.field_claims fc
    where fc.clinic_id = {sql_literal(row["clinic_id"])}::uuid
      and fc.entity_type = 'clinic'
      and fc.field_path = claim_input.field_path
      and fc.value = claim_input.value
      and fc.agent_name = claim_input.agent_name
  )
  returning id
),
updated_review as (
  update public.review_queue
  set payload = payload || jsonb_build_object(
    'source_records_captured_at', now(),
    'source_records_captured', (select count(*) from available_sources),
    'field_claims_captured_at', now(),
    'field_claims_captured', true,
    'field_claims_found', {len(claims)},
    'field_claims_created', (select count(*) from inserted_claims)
  )
  where id = {sql_literal(row["id"])}::uuid
  returning id
),
event as (
  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    clinic_id,
    payload
  )
  values (
    'enrichment_review_claims_captured',
    'admin',
    {sql_literal(admin_email)},
    'review_queue',
    {sql_literal(row["id"])}::uuid,
    {sql_literal(row["clinic_id"])}::uuid,
    jsonb_build_object(
      'review_id', {sql_literal(row["id"])},
      'source_urls_found', {len(urls)},
      'field_claims_found', {len(claims)},
      'field_claims_created', (select count(*) from inserted_claims)
    )
  )
  returning id
)
select jsonb_build_object(
  'review_id', {sql_literal(row["id"])},
  'title', {sql_literal(row.get("title"))},
  'source_urls_found', {len(urls)},
  'source_records_created', (select count(*) from inserted_sources),
  'field_claims_found', {len(claims)},
  'field_claims_created', (select count(*) from inserted_claims)
);
"""
    return json.loads(run_psql(sql, local_env))


def dry_run_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for row in rows:
        payload = row.get("payload") or {}
        items.append(
            {
                "review_id": row.get("id"),
                "title": row.get("title"),
                "source_urls": len(source_urls(payload)),
                "field_claims": len(field_claims(payload)),
            }
        )
    return {
        "mode": "dry_run",
        "reviews": len(rows),
        "source_urls": sum(item["source_urls"] for item in items),
        "field_claims": sum(item["field_claims"] for item in items),
        "items": items,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-id", help="Capture one clinic_profile_enrichment review item.")
    parser.add_argument("--include-captured", action="store_true", help="Include reviews already marked as captured.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--admin-email", help="Admin email used for audit attribution.")
    parser.add_argument("--apply", action="store_true", help="Write source_records and field_claims.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    local_env = load_env_file()
    rows = fetch_reviews(args.review_id, args.include_captured, args.limit, local_env)
    if not args.apply:
        print(json.dumps(dry_run_summary(rows), ensure_ascii=False, indent=2))
        return 0

    admin_email = args.admin_email or get_default_admin_email(local_env)
    results = [capture_review(row, admin_email, local_env) for row in rows]
    print(
        json.dumps(
            {
                "mode": "apply",
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "reviews": len(results),
                "source_records_created": sum(int(item.get("source_records_created") or 0) for item in results),
                "field_claims_created": sum(int(item.get("field_claims_created") or 0) for item in results),
                "items": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
