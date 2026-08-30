#!/usr/bin/env python3
"""Create internal shadow-extraction review cards from existing clinic sources.

Default mode is dry-run. Apply mode creates or refreshes internal
clinic_profile_enrichment review cards only; it never edits clinics or publishes
public pages.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError

from capture_source_snapshot import FetchResult, fetch_url
from extract_clinic_profile_shadow import extract_from_fetch
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal
from submit_shadow_extraction_review import create_review, review_payload
from verify_clinic_profile_shadow import verify_extraction


BATCH_NAME = "source-shadow-review"
BATCH_VERSION = "2026-08-30"


FetchFn = Callable[..., FetchResult]
CreateReviewFn = Callable[[str, dict[str, Any], str, dict[str, str], bool, bool], dict[str, Any]]

PENDING_FIELD_TARGETS = {
    "address": {"locations"},
    "contact": {"email", "telefono", "instagram"},
    "services": {"services"},
    "specialties": {"specialties"},
    "units": {"unidades"},
    "specialists": {"profesionales"},
    "technology": {"tech"},
    "years_in_practice": {"years_in_practice"},
    "specialists_count": {"specialists_count"},
    "team_credentialing_visible": {"team_credentialing_visible"},
    "public_pricing": {"public_pricing"},
}


def today_batch() -> str:
    return BATCH_NAME + "-" + datetime.now(timezone.utc).date().isoformat()


def load_clinic_sources(
    limit: int,
    clinic_slug: str | None,
    source_id: str | None,
    local_env: dict[str, str],
) -> list[dict[str, Any]]:
    clinic_filter = f"and c.slug = {sql_literal(clinic_slug)}" if clinic_slug else ""
    source_filter = f"and sr.id = {sql_literal(source_id)}::uuid" if source_id else ""
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.pending_count desc, items.has_open_review asc, items.team_source_priority desc, items.retrieved_at desc), '[]'::jsonb)
from (
  select
    sr.id as source_record_id,
    sr.source_type,
    sr.source_url,
    sr.source_title,
    sr.retrieved_at,
    cardinality(candidate.pending_fields) as pending_count,
    candidate.pending_fields,
    'specialists' = any(candidate.pending_fields) as specialists_pending,
    case
      when 'specialists' = any(candidate.pending_fields)
        and (
          sr.source_type = 'official_team_page'
          or coalesce(sr.source_title, '') ~* '(^|[^[:alpha:]])(equipo|profesionales|especialistas|doctor|doctora|doctores|doctoras|doctors|team|staff|quienes)([^[:alpha:]]|$)'
          or sr.source_url ~* '(^|[/_.-])(equipo|equipo-medico|equipo-medicos|cuadro-medico|cuadro-medicos|profesionales|especialistas|doctor|doctora|doctores|doctoras|doctors|team|staff|about|quienes-somos|quienes)([/_.?#-]|$)'
        )
        then 1
      else 0
    end as team_source_priority,
    c.id as clinic_id,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.status as clinic_status,
    (
      select jsonb_build_object(
        'id', rq.id,
        'title', rq.title,
        'priority', rq.priority,
        'created_at', rq.created_at
      )
      from public.review_queue rq
      where rq.clinic_id = c.id
        and rq.status = 'open'
        and rq.review_type = 'clinic_profile_enrichment'
        and rq.payload ->> 'source_url' = sr.source_url
      order by rq.priority desc, rq.created_at asc
      limit 1
    ) as open_review,
    (
      select jsonb_build_object(
        'id', rq.id,
        'title', rq.title,
        'priority', rq.priority,
        'source_url', rq.payload ->> 'source_url',
        'created_at', rq.created_at
      )
      from public.review_queue rq
      where rq.clinic_id = c.id
        and rq.status = 'open'
        and rq.review_type = 'clinic_profile_enrichment'
      order by rq.priority desc, rq.created_at asc
      limit 1
    ) as open_clinic_review,
    exists (
      select 1
      from public.review_queue rq
      where rq.clinic_id = c.id
        and rq.status = 'open'
        and rq.review_type = 'clinic_profile_enrichment'
        and rq.payload ->> 'source_url' = sr.source_url
    ) as has_open_review,
    exists (
      select 1
      from public.review_queue rq
      where rq.clinic_id = c.id
        and rq.status = 'open'
        and rq.review_type = 'clinic_profile_enrichment'
    ) as has_open_clinic_review
  from public.source_records sr
  join public.clinics c on c.id = sr.clinic_id
  cross join lateral (
    select array_remove(array[
      case when length(btrim(coalesce(c.summary, c.current_data ->> 'summary', ''))) < 120 then 'summary' end,
      case when nullif(btrim(coalesce(c.website, c.current_data ->> 'web', '')), '') is null then 'website' end,
      case when nullif(btrim(coalesce(c.address, c.current_data ->> 'address', '')), '') is null then 'address' end,
      case
        when nullif(btrim(coalesce(c.current_data ->> 'email', '')), '') is null
          and nullif(btrim(coalesce(c.current_data ->> 'telefono', c.current_data ->> 'phone', c.current_data ->> 'telephone', '')), '') is null
          then 'contact'
      end,
      case
        when nullif(btrim(coalesce(
          c.current_data ->> 'years_in_practice',
          c.current_data ->> 'years_active',
          c.current_data ->> 'founded_year',
          c.current_data #>> '{{transparency,years_in_practice}}',
          c.current_data #>> '{{transparency,years_active}}',
          ''
        )), '') is null
          then 'years_in_practice'
      end,
      case
        when nullif(btrim(coalesce(
          c.current_data ->> 'specialists_count',
          c.current_data ->> 'num_specialists',
          c.current_data ->> 'specialists_public_count',
          c.current_data #>> '{{transparency,specialists_count}}',
          ''
        )), '') is null
          then 'specialists_count'
      end,
      case
        when nullif(btrim(coalesce(
          c.current_data ->> 'team_credentialing_visible',
          c.current_data ->> 'medical_license_visible',
          c.current_data ->> 'colegiacion_visible',
          c.current_data #>> '{{team,credentialing_visible}}',
          ''
        )), '') is null
          then 'team_credentialing_visible'
      end,
      case
        when nullif(btrim(coalesce(
          c.current_data ->> 'public_pricing',
          c.current_data ->> 'prices_public',
          c.current_data ->> 'price_public',
          c.current_data #>> '{{prices,public_status}}',
          ''
        )), '') is null
          then 'public_pricing'
      end,
      case
        when coalesce(jsonb_array_length(case when jsonb_typeof(c.current_data -> 'services') = 'array' then c.current_data -> 'services' else '[]'::jsonb end), 0) = 0
          then 'services'
      end,
      case
        when coalesce(jsonb_array_length(case when jsonb_typeof(c.current_data -> 'specialties') = 'array' then c.current_data -> 'specialties' else '[]'::jsonb end), 0) = 0
          then 'specialties'
      end,
      case
        when coalesce(jsonb_array_length(case when jsonb_typeof(c.current_data -> 'unidades') = 'array' then c.current_data -> 'unidades' else '[]'::jsonb end), 0) = 0
          then 'units'
      end,
      case
        when coalesce(jsonb_array_length(case when jsonb_typeof(c.current_data -> 'profesionales') = 'array' then c.current_data -> 'profesionales' else '[]'::jsonb end), 0) = 0
          then 'specialists'
      end,
      case
        when case
          when jsonb_typeof(c.current_data -> 'tech') = 'array'
            then coalesce(jsonb_array_length(c.current_data -> 'tech'), 0) > 0
          else nullif(btrim(coalesce(c.current_data ->> 'tech', '')), '') is not null
        end is not true
          then 'technology'
      end
    ], null) as pending_fields
  ) candidate
  where sr.entity_type = 'clinic'
    and sr.source_url ~* '^https?://'
    and c.status <> 'archived'
    and cardinality(candidate.pending_fields) > 0
    {clinic_filter}
    {source_filter}
  order by cardinality(candidate.pending_fields) desc, has_open_review asc, team_source_priority desc, sr.retrieved_at desc, sr.created_at desc
  limit {max(1, min(100, int(limit)))}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def payload_for_source(source: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    payload = review_payload(str(source.get("clinic_slug") or ""), verification)
    warnings = list(payload.get("warnings") or [])
    warnings.insert(0, "Fuente existente revisada en modo sombra; confirmar antes de guardar.")
    payload.update({
        "batch": today_batch(),
        "batch_name": BATCH_NAME,
        "batch_version": BATCH_VERSION,
        "source_record_id": source.get("source_record_id"),
        "clinic_id": source.get("clinic_id"),
        "clinic_slug": source.get("clinic_slug"),
        "clinic_name": source.get("clinic_name"),
        "source_url": source.get("source_url"),
        "warnings": warnings,
    })
    return payload


def proposed_field_counts(proposed_fields: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in proposed_fields.items():
        if isinstance(value, list):
            counts[key] = len(value)
        elif value in (None, ""):
            counts[key] = 0
        else:
            counts[key] = 1
    return counts


def filter_proposed_fields_for_pending(
    proposed_fields: dict[str, Any],
    pending_fields: list[str],
) -> dict[str, Any]:
    allowed = set()
    for field in pending_fields:
        allowed.update(PENDING_FIELD_TARGETS.get(str(field), set()))
    if not allowed:
        return {}
    return {
        key: value
        for key, value in proposed_fields.items()
        if key in allowed
    }


def process_source(
    source: dict[str, Any],
    args: argparse.Namespace,
    admin_email: str,
    local_env: dict[str, str],
    fetcher: FetchFn = fetch_url,
    review_creator: CreateReviewFn = create_review,
) -> dict[str, Any]:
    clinic_slug = str(source.get("clinic_slug") or "")
    source_url = str(source.get("source_url") or "")
    result = {
        "source_record_id": source.get("source_record_id"),
        "clinic_slug": clinic_slug,
        "clinic_name": source.get("clinic_name"),
        "source_type": source.get("source_type"),
        "source_url": source_url,
        "pending_count": source.get("pending_count") or 0,
        "pending_fields": source.get("pending_fields") or [],
        "specialists_pending": bool(source.get("specialists_pending")),
        "team_source_priority": source.get("team_source_priority") or 0,
        "open_review": source.get("open_review"),
        "open_clinic_review": source.get("open_clinic_review"),
    }

    if not clinic_slug or not source_url:
        return {**result, "status": "skipped", "reason": "missing clinic slug or source URL"}

    if source.get("has_open_review") and not args.replace_existing:
        return {**result, "status": "skipped", "reason": "open enrichment review already exists"}

    if (
        source.get("has_open_clinic_review")
        and not source.get("has_open_review")
        and not args.allow_multiple_open_clinic_reviews
    ):
        return {**result, "status": "skipped", "reason": "open enrichment review already exists for this clinic"}

    try:
        extraction = extract_from_fetch(fetcher(source_url, timeout=args.timeout))
        verification = verify_extraction(extraction)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return {**result, "status": "failed", "error": str(error)}

    payload = payload_for_source(source, verification)
    payload["proposed_fields"] = filter_proposed_fields_for_pending(
        payload.get("proposed_fields") or {},
        source.get("pending_fields") or [],
    )
    proposed_fields = payload.get("proposed_fields") or {}
    result.update({
        "status": "ready" if proposed_fields else "empty",
        "proposed_fields": sorted(proposed_fields.keys()),
        "proposed_field_counts": proposed_field_counts(proposed_fields),
        "verification_summary": payload.get("verification_summary") or {},
    })

    if args.apply and proposed_fields:
        result["created_review"] = review_creator(
            clinic_slug,
            payload,
            admin_email,
            local_env,
            args.replace_existing,
            args.allow_multiple_open_clinic_reviews,
        )
    return result


def duplicate_clinic_result(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_record_id": source.get("source_record_id"),
        "clinic_slug": source.get("clinic_slug"),
        "clinic_name": source.get("clinic_name"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
        "pending_count": source.get("pending_count") or 0,
        "pending_fields": source.get("pending_fields") or [],
        "specialists_pending": bool(source.get("specialists_pending")),
        "team_source_priority": source.get("team_source_priority") or 0,
        "status": "skipped",
        "reason": "another source for this clinic is already queued in this batch",
    }


def process_sources(
    sources: list[dict[str, Any]],
    args: argparse.Namespace,
    admin_email: str,
    local_env: dict[str, str],
    fetcher: FetchFn = fetch_url,
    review_creator: CreateReviewFn = create_review,
) -> list[dict[str, Any]]:
    results = []
    queued_clinics = set()
    for source in sources:
        clinic_slug = str(source.get("clinic_slug") or "")
        if (
            clinic_slug
            and clinic_slug in queued_clinics
            and not args.allow_multiple_open_clinic_reviews
        ):
            results.append(duplicate_clinic_result(source))
            continue

        result = process_source(source, args, admin_email, local_env, fetcher, review_creator)
        results.append(result)
        if clinic_slug and result.get("status") in {"ready", "skipped"}:
            queued_clinics.add(clinic_slug)
    return results


def summarize_results(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "sources_seen": len(results),
        "ready": sum(1 for item in results if item.get("status") == "ready"),
        "empty": sum(1 for item in results if item.get("status") == "empty"),
        "skipped": sum(1 for item in results if item.get("status") == "skipped"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
        "created_or_updated": sum(1 for item in results if item.get("created_review")),
    }


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "clinic_slug": item.get("clinic_slug"),
        "clinic_name": item.get("clinic_name"),
        "source_type": item.get("source_type"),
        "source_url": item.get("source_url"),
        "status": item.get("status"),
        "reason": item.get("reason"),
        "pending_count": item.get("pending_count"),
        "pending_fields": item.get("pending_fields") or [],
        "proposed_fields": item.get("proposed_fields") or [],
        "proposed_field_counts": item.get("proposed_field_counts") or {},
        "has_open_review": bool(item.get("open_review")),
        "has_open_clinic_review": bool(item.get("open_clinic_review")),
    }


def compact_output(output: dict[str, Any]) -> dict[str, Any]:
    items = output.get("items") if isinstance(output.get("items"), list) else []
    compact_items = [compact_item(item) for item in items if isinstance(item, dict)]
    return {
        "mode": output.get("mode"),
        "writes_data": output.get("mode") == "apply",
        "sources_seen": output.get("sources_seen"),
        "ready": output.get("ready"),
        "empty": output.get("empty"),
        "skipped": output.get("skipped"),
        "failed": output.get("failed"),
        "created_or_updated": output.get("created_or_updated"),
        "ready_items": [item for item in compact_items if item.get("status") == "ready"],
        "skipped_items": [item for item in compact_items if item.get("status") == "skipped"],
        "failed_items": [item for item in compact_items if item.get("status") == "failed"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--clinic-slug", help="Process sources for one existing clinic.")
    parser.add_argument("--source-id", help="Process one source_records row.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--admin-email", help="Admin email assigned to created review cards.")
    parser.add_argument("--replace-existing", action="store_true", help="Refresh an existing open review for the same source.")
    parser.add_argument(
        "--allow-multiple-open-clinic-reviews",
        action="store_true",
        help="Allow more than one open enrichment card for the same clinic.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create internal clinic_profile_enrichment review cards. Never publishes or edits clinics.",
    )
    parser.add_argument("--compact", action="store_true", help="Print a compact summary without full verification details.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    sources = load_clinic_sources(args.limit, args.clinic_slug, args.source_id, local_env)
    results = process_sources(sources, args, admin_email, local_env)
    output = {
        "mode": "apply" if args.apply else "dry_run",
        **summarize_results(results),
        "items": results,
    }
    if args.compact:
        output = compact_output(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
