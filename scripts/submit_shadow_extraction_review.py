#!/usr/bin/env python3
"""Submit shadow extraction findings as an internal review card.

This converts extract -> verify -> rules output into a clinic_profile_enrichment
review item for an existing clinic. It never updates the public clinic profile.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from capture_source_snapshot import fetch_url
from extract_clinic_profile_shadow import extract_from_fetch
from submit_discovery_candidates import (
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)
from verify_clinic_profile_shadow import verify_extraction


ROOT = Path(__file__).resolve().parents[1]


FIELD_MAP = {
    "contact.email": "email",
    "contact.phone": "telefono",
    "contact.instagram": "instagram",
    "services.list": "services",
    "specialties.list": "specialties",
    "technologies.list": "tech",
}


def today_batch() -> str:
    return "shadow-extraction-" + datetime.now(timezone.utc).date().isoformat()


def load_extraction(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("extraction JSON must contain an object")
    return data


def decision_by_field(verification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decisions = verification.get("rule_decisions") or []
    result = {}
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("field_path"):
            result[str(decision["field_path"])] = decision
    return result


def proposed_fields_from_verification(verification: dict[str, Any]) -> dict[str, Any]:
    decisions = decision_by_field(verification)
    fields: dict[str, Any] = {}
    for claim in verification.get("verified_claims") or []:
        if not isinstance(claim, dict):
            continue
        field_path = str(claim.get("field_path") or "")
        target = FIELD_MAP.get(field_path)
        if not target:
            continue
        decision = decisions.get(field_path) or {}
        if decision.get("action") == "reject" or claim.get("verifier_verdict") == "rejected":
            continue
        value = claim.get("value")
        if target == "tech" and isinstance(value, list):
            fields[target] = ", ".join(str(item) for item in value if str(item).strip())
        else:
            fields[target] = value
    return {key: value for key, value in fields.items() if value}


def source_urls_from_verification(verification: dict[str, Any]) -> list[str]:
    urls = []
    for claim in verification.get("verified_claims") or []:
        if isinstance(claim, dict) and claim.get("source_url"):
            urls.append(str(claim["source_url"]))
    if verification.get("source_url"):
        urls.append(str(verification["source_url"]))
    seen = set()
    clean = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            clean.append(url)
    return clean


def review_payload(clinic_slug: str, verification: dict[str, Any]) -> dict[str, Any]:
    fields = proposed_fields_from_verification(verification)
    return {
        "mode": "shadow",
        "proposal_batch": today_batch(),
        "clinic_slug": clinic_slug,
        "source_urls": source_urls_from_verification(verification),
        "warnings": [
            "Propuesta generada por extractor/verificador shadow; revisar antes de guardar."
        ],
        "proposed_fields": fields,
        "field_claims": verification.get("verified_claims") or [],
        "rule_decisions": verification.get("rule_decisions") or [],
        "verification_summary": verification.get("summary") or {},
    }


def create_review(clinic_slug: str, payload: dict[str, Any], admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    if not payload.get("proposed_fields"):
        return {"status": "empty", "slug": clinic_slug}
    source_url = (payload.get("source_urls") or [""])[0]
    sql_payload = json.dumps(payload, ensure_ascii=False)
    sql = f"""
with target as (
  select id, slug, display_name, city, country, website
  from public.clinics
  where slug = {sql_literal(clinic_slug)}
),
existing as (
  select rq.id, rq.title
  from public.review_queue rq
  join target t on t.id = rq.clinic_id
  where rq.review_type = 'clinic_profile_enrichment'
    and rq.status = 'open'
    and rq.payload ->> 'source_url' = {sql_literal(source_url)}
  limit 1
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
    'clinic_profile_enrichment',
    'Revisar extracción shadow: ' || t.display_name,
    'current_data',
    60,
    'open',
    jsonb_strip_nulls(
      {sql_literal(sql_payload)}::jsonb ||
      jsonb_build_object(
        'clinic_id', t.id,
        'clinic_slug', t.slug,
        'clinic_name', t.display_name,
        'clinic_city', t.city,
        'clinic_country', t.country,
        'website', t.website,
        'source_url', {sql_literal(source_url)}
      )
    ),
    {sql_literal(admin_email)}
  from target t
  where not exists (select 1 from existing)
  returning id, title
),
resolved as (
  select 'inserted' as status, id, title from inserted
  union all
  select 'existing' as status, id, title from existing
  where not exists (select 1 from inserted)
)
select coalesce(jsonb_agg(to_jsonb(resolved.*)), '[]'::jsonb)
from resolved;
"""
    rows = json.loads(run_psql(sql, local_env) or "[]")
    if not rows:
        return {"status": "missing", "slug": clinic_slug}
    return rows[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Fetch and extract a clinic source URL.")
    source.add_argument("--extraction-json", type=Path, help="Use existing extraction JSON.")
    parser.add_argument("--clinic-slug", required=True, help="Existing Diuvita clinic slug.")
    parser.add_argument("--admin-email", help="Admin email used for assignment/audit.")
    parser.add_argument("--apply", action="store_true", help="Create the review card in Supabase.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.url:
        extraction = extract_from_fetch(fetch_url(args.url))
    else:
        extraction = load_extraction(args.extraction_json)
    verification = verify_extraction(extraction)
    payload = review_payload(args.clinic_slug, verification)

    if not args.apply:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    result = create_review(args.clinic_slug, payload, admin_email, local_env)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
