#!/usr/bin/env python3
"""Capture verified shadow claims directly from hydrated clinic sources.

This is an internal evidence step. It reads source_records with stored excerpts,
extracts/verifies claims, and can store field_claims linked to the source. It
never edits clinic profiles, creates review cards or publishes public pages.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from capture_enrichment_review_claims import field_claims, values_claim_sql
from extract_clinic_profile_shadow import build_claims, build_profile
from hydrate_source_records import first_json_line
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal
from verify_clinic_profile_shadow import verify_extraction


CAPTURER_NAME = "vitalarga-source-shadow-claims"
CAPTURER_VERSION = "2026-08-30"


def load_hydrated_sources(
    limit: int,
    clinic_slug: str | None,
    source_id: str | None,
    include_claimed: bool,
    local_env: dict[str, str],
) -> list[dict[str, Any]]:
    clinic_filter = f"and c.slug = {sql_literal(clinic_slug)}" if clinic_slug else ""
    source_filter = f"and sr.id = {sql_literal(source_id)}::uuid" if source_id else ""
    claimed_filter = "true" if include_claimed else "not exists (select 1 from public.field_claims fc where fc.source_record_id = sr.id)"
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.status_order, items.claim_priority desc, items.retrieved_at desc), '[]'::jsonb)
from (
  select
    sr.id as source_record_id,
    sr.clinic_id,
    sr.source_url,
    sr.source_title,
    sr.source_type,
    sr.raw_excerpt,
    sr.content_hash,
    sr.retrieved_at,
    sr.metadata,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.status as clinic_status,
    case when c.status = 'published' then 0 else 1 end as status_order,
    case
      when sr.source_type in ('official_location_page', 'official_team_page') then 2
      when sr.source_type in ('official_website', 'website') then 1
      else 0
    end as claim_priority
  from public.source_records sr
  join public.clinics c on c.id = sr.clinic_id
  where sr.entity_type = 'clinic'
    and c.status in ('published', 'preliminary')
    and nullif(btrim(coalesce(sr.raw_excerpt, '')), '') is not null
    and {claimed_filter}
    {clinic_filter}
    {source_filter}
  order by status_order, claim_priority desc, sr.retrieved_at desc
  limit {max(1, min(200, int(limit)))}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def extraction_from_source(source: dict[str, Any]) -> dict[str, Any]:
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    source_url = str(source.get("source_url") or "")
    final_url = str(metadata.get("final_url") or source_url)
    snapshot = {
        "source_url": source_url,
        "final_url": final_url,
        "source_title": source.get("source_title"),
        "source_type": source.get("source_type"),
        "retrieved_at": source.get("retrieved_at"),
        "http_status": metadata.get("http_status"),
        "content_type": metadata.get("content_type"),
        "request_profile": metadata.get("request_profile"),
        "content_sha256": source.get("content_hash"),
        "text_sha256": metadata.get("text_sha256"),
        "text_excerpt": source.get("raw_excerpt"),
    }
    claims = build_claims(snapshot)
    return {
        "workflow": "EXTRACT_CLINIC_PROFILE",
        "mode": "shadow",
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": snapshot,
        "candidate_profile": build_profile(snapshot),
        "field_claims": claims,
    }


def claims_from_verification(verification: dict[str, Any]) -> list[dict[str, Any]]:
    payload = {
        "field_claims": verification.get("verified_claims") or [],
        "rule_decisions": verification.get("rule_decisions") or [],
    }
    return field_claims(payload)


def insert_claims_sql(source: dict[str, Any], claims: list[dict[str, Any]], admin_email: str) -> str:
    if not claims:
        return f"""
select jsonb_build_object(
  'source_record_id', {sql_literal(source.get("source_record_id"))},
  'field_claims_found', 0,
  'field_claims_created', 0
);
"""
    clinic_id = sql_literal(source.get("clinic_id")) + "::uuid"
    source_record_id = sql_literal(source.get("source_record_id")) + "::uuid"
    return f"""
with claim_input(field_path, value, confidence, verification_status, agent_name, agent_version) as (
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
    {clinic_id},
    'clinic',
    {clinic_id},
    claim_input.field_path,
    claim_input.value,
    claim_input.value,
    {source_record_id},
    claim_input.agent_name,
    claim_input.agent_version,
    claim_input.confidence,
    claim_input.verification_status,
    exists (
      select 1
      from public.human_overrides ho
      where ho.clinic_id = {clinic_id}
        and ho.entity_type = 'clinic'
        and ho.field_path = claim_input.field_path
        and ho.locked = true
    )
  from claim_input
  where not exists (
    select 1
    from public.field_claims fc
    where fc.clinic_id = {clinic_id}
      and fc.entity_type = 'clinic'
      and fc.field_path = claim_input.field_path
      and fc.value = claim_input.value
      and fc.source_record_id = {source_record_id}
      and fc.agent_name = claim_input.agent_name
  )
  returning id
),
updated_source as (
  update public.source_records
  set metadata = coalesce(metadata, '{{}}'::jsonb) || jsonb_build_object(
    'source_shadow_claims_captured_at', now(),
    'source_shadow_claims_captured_by', {sql_literal(admin_email)},
    'source_shadow_claims_capturer', {sql_literal(CAPTURER_NAME)},
    'source_shadow_claims_capturer_version', {sql_literal(CAPTURER_VERSION)},
    'source_shadow_claims_found', {len(claims)},
    'source_shadow_claims_created', (select count(*) from inserted_claims)
  )
  where id = {source_record_id}
  returning id
)
select jsonb_build_object(
  'source_record_id', {sql_literal(source.get("source_record_id"))},
  'clinic_slug', {sql_literal(source.get("clinic_slug"))},
  'field_claims_found', {len(claims)},
  'field_claims_created', (select count(*) from inserted_claims),
  'source_updated', exists(select 1 from updated_source)
);
"""


def process_source(
    source: dict[str, Any],
    args: argparse.Namespace,
    admin_email: str,
    local_env: dict[str, str],
) -> dict[str, Any]:
    extraction = extraction_from_source(source)
    verification = verify_extraction(extraction)
    claims = claims_from_verification(verification)
    result = {
        "source_record_id": source.get("source_record_id"),
        "clinic_slug": source.get("clinic_slug"),
        "clinic_name": source.get("clinic_name"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
        "status": "ready" if claims else "empty",
        "field_claims_found": len(claims),
        "verification_summary": verification.get("summary") or {},
        "claim_fields": sorted({str(claim.get("field_path")) for claim in claims if claim.get("field_path")}),
    }
    if args.apply and claims:
        result["captured"] = first_json_line(run_psql(insert_claims_sql(source, claims, admin_email), local_env))
    return result


def summarize(results: list[dict[str, Any]], apply: bool) -> dict[str, Any]:
    return {
        "mode": "apply" if apply else "dry_run",
        "writes_data": bool(apply),
        "sources_seen": len(results),
        "ready": sum(1 for item in results if item.get("status") == "ready"),
        "empty": sum(1 for item in results if item.get("status") == "empty"),
        "field_claims_found": sum(int(item.get("field_claims_found") or 0) for item in results),
        "field_claims_created": sum(int((item.get("captured") or {}).get("field_claims_created") or 0) for item in results),
        "items": results,
        "safety": "stores field_claims only; does not edit profiles, create reviews or publish the website",
    }


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    captured = item.get("captured") if isinstance(item.get("captured"), dict) else {}
    return {
        "clinic_slug": item.get("clinic_slug"),
        "clinic_name": item.get("clinic_name"),
        "source_type": item.get("source_type"),
        "source_url": item.get("source_url"),
        "status": item.get("status"),
        "field_claims_found": item.get("field_claims_found"),
        "field_claims_created": captured.get("field_claims_created"),
        "claim_fields": item.get("claim_fields") or [],
    }


def compact_output(output: dict[str, Any]) -> dict[str, Any]:
    items = output.get("items") if isinstance(output.get("items"), list) else []
    return {
        "mode": output.get("mode"),
        "writes_data": output.get("writes_data"),
        "sources_seen": output.get("sources_seen"),
        "ready": output.get("ready"),
        "empty": output.get("empty"),
        "field_claims_found": output.get("field_claims_found"),
        "field_claims_created": output.get("field_claims_created"),
        "items": [compact_item(item) for item in items if isinstance(item, dict)],
        "safety": output.get("safety"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--clinic-slug", help="Capture claims for one clinic slug.")
    parser.add_argument("--source-id", help="Capture claims for one source_records row.")
    parser.add_argument("--include-claimed", action="store_true", help="Re-process sources that already have linked claims.")
    parser.add_argument("--admin-email", help="Admin email used for audit attribution.")
    parser.add_argument("--apply", action="store_true", help="Store field_claims linked to source_records.")
    parser.add_argument("--compact", action="store_true", help="Print compact output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    sources = load_hydrated_sources(
        args.limit,
        args.clinic_slug,
        args.source_id,
        args.include_claimed,
        local_env,
    )
    results = [process_source(source, args, admin_email, local_env) for source in sources]
    output = summarize(results, args.apply)
    if args.compact:
        output = compact_output(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
