#!/usr/bin/env python3
"""Enrich an open candidate review with facts from another official source URL."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from capture_source_snapshot import fetch_url, normalize_space
from extract_clinic_profile_shadow import extract_from_fetch
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        clean = normalize_space(str(item or "")).strip(".,;:")
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if normalize_space(str(item or ""))]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def first_json_line(output: str) -> Any:
    for line in output.splitlines():
        clean = line.strip()
        if clean.startswith("{") or clean.startswith("["):
            return json.loads(clean)
    raise ValueError("No JSON row returned by psql.")


def extracted_professionals(extraction: dict[str, Any]) -> list[str]:
    profile = extraction.get("candidate_profile") or {}
    values = as_list(profile.get("professionals"))
    if values:
        return unique(values)
    for claim in extraction.get("field_claims") or []:
        if isinstance(claim, dict) and claim.get("field_path") == "professionals.published":
            return unique(as_list(claim.get("value")))
    return []


def add_source_urls(payload: dict[str, Any], candidate: dict[str, Any], source_url: str) -> list[str]:
    urls: list[str] = []
    urls.extend(as_list(candidate.get("source_url")))
    urls.extend(as_list(payload.get("candidate_source_url")))
    urls.extend(as_list(candidate.get("source_urls")))
    urls.extend(as_list(candidate.get("sources")))
    urls.extend(as_list(payload.get("source_urls")))
    urls.extend(as_list(payload.get("sources")))
    urls.append(source_url)
    return unique(urls)


def patched_payload(payload: dict[str, Any], extraction: dict[str, Any], source_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    professionals = extracted_professionals(extraction)
    if not professionals:
        return payload, {"status": "empty", "reason": "no professionals detected"}

    patched = json.loads(json.dumps(payload, ensure_ascii=False))
    candidate = dict(patched.get("candidate") or {})
    merged_professionals = unique(
        as_list(candidate.get("profesionales"))
        + as_list(candidate.get("professionals"))
        + professionals
    )
    source_urls = add_source_urls(patched, candidate, source_url)

    candidate["profesionales"] = merged_professionals
    candidate["source_urls"] = source_urls
    patched["candidate"] = candidate
    patched["source_urls"] = source_urls
    patched["enriched_at"] = now_iso()
    patched["enrichment_source_url"] = source_url
    existing_enrichments = patched.get("shadow_enrichments")
    if not isinstance(existing_enrichments, list):
        existing_enrichments = []
    enrichment = {
        "field": "profesionales",
        "source_url": source_url,
        "values": professionals,
        "agent_name": "vitalarga-candidate-enrichment",
        "agent_version": "2026-08-30",
    }
    if not any(
        isinstance(item, dict)
        and item.get("field") == enrichment["field"]
        and item.get("source_url") == enrichment["source_url"]
        for item in existing_enrichments
    ):
        existing_enrichments.append(enrichment)
    patched["shadow_enrichments"] = existing_enrichments
    patched["warnings"] = unique(
        as_list(patched.get("warnings"))
        + ["Especialistas detectados desde una página oficial; revisar antes de crear borrador."]
    )
    return patched, {
        "status": "patched",
        "professionals": merged_professionals,
        "source_urls": source_urls,
    }


def load_review(review_id: str, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
select jsonb_build_object(
  'id', id,
  'title', title,
  'status', status,
  'review_type', review_type,
  'payload', payload
)
from public.review_queue
where id = {sql_literal(review_id)}::uuid
  and review_type = 'candidate_clinic'
  and status = 'open';
"""
    output = run_psql(sql, local_env).strip()
    if not output:
        raise SystemExit("Open candidate review not found.")
    return json.loads(output)


def source_title(extraction: dict[str, Any]) -> str:
    source = extraction.get("source") or {}
    return normalize_space(str(source.get("source_title") or ""))[:180]


def source_excerpt(extraction: dict[str, Any]) -> str:
    source = extraction.get("source") or {}
    return normalize_space(str(source.get("text_excerpt") or ""))[:1000]


def ensure_source_record_sql(review_id: str, source_url: str, extraction: dict[str, Any]) -> str:
    return f"""
insert into public.source_records (
  entity_type,
  source_url,
  source_title,
  source_type,
  raw_excerpt,
  metadata
)
select
  'candidate_clinic',
  {sql_literal(source_url)},
  {sql_literal(source_title(extraction))},
  'team_page',
  {sql_literal(source_excerpt(extraction))},
  jsonb_build_object(
    'review_id', {sql_literal(review_id)},
    'purpose', 'team_public_professionals',
    'mode', 'shadow'
  )
where not exists (
  select 1
  from public.source_records
  where entity_type = 'candidate_clinic'
    and source_url = {sql_literal(source_url)}
    and metadata ->> 'review_id' = {sql_literal(review_id)}
);
"""


def update_review(review_id: str, payload: dict[str, Any], extraction: dict[str, Any], source_url: str, local_env: dict[str, str]) -> dict[str, Any]:
    payload_json = json.dumps(payload, ensure_ascii=False)
    sql = (
        ensure_source_record_sql(review_id, source_url, extraction)
        + f"""
update public.review_queue
set payload = {sql_literal(payload_json)}::jsonb
where id = {sql_literal(review_id)}::uuid
  and review_type = 'candidate_clinic'
  and status = 'open'
returning jsonb_build_object(
  'id', id,
  'title', title,
  'professionals', payload #> '{{candidate,profesionales}}',
  'source_urls', payload #> '{{candidate,source_urls}}'
);
"""
    )
    output = run_psql(sql, local_env)
    if not output.strip():
        raise SystemExit("Candidate review was not updated.")
    return first_json_line(output)


def load_extraction(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("extraction JSON must contain an object")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-id", required=True, help="Open candidate_clinic review id.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Official source URL to extract.")
    source.add_argument("--extraction-json", type=Path, help="Use existing extractor output.")
    parser.add_argument("--apply", action="store_true", help="Update Supabase.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.url:
        extraction = extract_from_fetch(fetch_url(args.url))
        source_url = str((extraction.get("source") or {}).get("final_url") or args.url)
    else:
        extraction = load_extraction(args.extraction_json)
        source = extraction.get("source") or {}
        source_url = str(source.get("final_url") or source.get("source_url") or "")
    if not source_url:
        raise SystemExit("No source URL found.")

    local_env = load_env_file()
    review = load_review(args.review_id, local_env)
    payload, summary = patched_payload(review.get("payload") or {}, extraction, source_url)
    if not args.apply:
        print(json.dumps({"review_id": args.review_id, "summary": summary, "payload": payload}, ensure_ascii=False, indent=2))
        return 0
    if summary.get("status") != "patched":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    result = update_review(args.review_id, payload, extraction, source_url, local_env)
    print(json.dumps({"status": "updated", "review": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
