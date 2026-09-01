#!/usr/bin/env python3
"""Process source-backed DISCOVER_CLINIC recommendations into review cards.

This is a narrow bridge for Daniel/public recommendations that already include
an official URL. It never edits clinics or publishes pages; in apply mode it
only completes the discovery job through the existing review_queue path.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError

from extract_clinic_profile_shadow import claim_website, extract_from_fetch, fetch_url
from submit_discovery_candidates import (
    complete_job,
    get_default_admin_email,
    load_env_file,
    run_psql,
    sql_literal,
)


JOB_TYPE = "DISCOVER_CLINIC"
WORKER_NAME = "vitalarga-source-recommendation-worker"


def clean_str(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def clean_http_url(value: Any) -> str:
    clean = clean_str(value)
    return clean if re.match(r"^https?://", clean, re.I) else ""


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = clean_str(value)
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def first_source_url(input_data: dict[str, Any]) -> str:
    candidates = [
        input_data.get("source_url"),
        input_data.get("official_url"),
        input_data.get("website"),
        input_data.get("web"),
    ]
    candidates.extend(as_list(input_data.get("source_urls")))
    for candidate in candidates:
        url = clean_http_url(candidate)
        if url:
            return url
    return ""


def first_location_city(profile: dict[str, Any]) -> str:
    locations = profile.get("locations")
    if not isinstance(locations, list):
        return ""
    for location in locations:
        if isinstance(location, dict):
            city = clean_str(location.get("city"))
            if city:
                return city
    return ""


def requested_info_label(input_data: dict[str, Any]) -> str:
    return clean_str(
        input_data.get("requested_info_label")
        or input_data.get("operator_requested_field_summary")
        or input_data.get("requested_info")
        or "Recomendación de clínica"
    )


def operator_note(input_data: dict[str, Any]) -> str:
    return clean_str(input_data.get("operator_note") or input_data.get("note"))


def discovery_confidence(profile: dict[str, Any], input_data: dict[str, Any]) -> float:
    score = 0.55
    if clean_str(profile.get("name")) or clean_str(input_data.get("clinic_name")):
        score += 0.10
    if clean_str(profile.get("website")):
        score += 0.10
    if clean_str(input_data.get("website") or input_data.get("web")):
        score += 0.05
    if first_location_city(profile) or clean_str(input_data.get("city")):
        score += 0.05
    if profile.get("summary"):
        score += 0.04
    if profile.get("services") or profile.get("specialties") or profile.get("units"):
        score += 0.04
    return round(min(score, 0.82), 2)


def compact_profile_counts(profile: dict[str, Any]) -> dict[str, int]:
    fields = ("locations", "services", "specialties", "units", "professionals", "technologies")
    counts: dict[str, int] = {}
    for field in fields:
        value = profile.get(field)
        if isinstance(value, list) and value:
            counts[field] = len(value)
    if profile.get("emails"):
        counts["emails"] = len(profile["emails"])
    if profile.get("phones"):
        counts["phones"] = len(profile["phones"])
    return counts


def recommendation_context(input_data: dict[str, Any], source_url: str) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "source": clean_str(input_data.get("source") or "unknown_recommendation"),
            "requested_info": clean_str(input_data.get("requested_info")),
            "requested_info_label": requested_info_label(input_data),
            "operator_note": operator_note(input_data),
            "source_url": source_url,
            "allowed_output": clean_str(input_data.get("allowed_output") or "review_queue_proposal_only"),
        }.items()
        if value
    }


def build_candidate(job: dict[str, Any], extraction: dict[str, Any], source_url: str) -> dict[str, Any]:
    input_data = as_dict(job.get("input"))
    profile = as_dict(extraction.get("candidate_profile"))
    source = as_dict(extraction.get("source"))
    final_url = clean_http_url(source.get("final_url")) or source_url
    website = (
        clean_http_url(input_data.get("website"))
        or clean_http_url(input_data.get("web"))
        or clean_http_url(profile.get("website"))
        or clean_http_url(claim_website(final_url))
    )
    emails = [clean_str(item) for item in as_list(profile.get("emails")) if clean_str(item)]
    phones = [clean_str(item) for item in as_list(profile.get("phones")) if clean_str(item)]
    instagram = [clean_str(item) for item in as_list(profile.get("instagram")) if clean_str(item)]
    candidate = {
        "name": clean_str(input_data.get("clinic_name")) or clean_str(profile.get("name")),
        "website": website,
        "city": clean_str(input_data.get("city")) or first_location_city(profile),
        "country": clean_str(input_data.get("country")) or "España",
        "source_url": final_url,
        "source_urls": unique([final_url, source_url, *[clean_http_url(item) for item in as_list(input_data.get("source_urls"))]]),
        "discovery_confidence": discovery_confidence(profile, input_data),
        "summary": clean_str(profile.get("summary")),
        "services": profile.get("services") if isinstance(profile.get("services"), list) else [],
        "specialties": profile.get("specialties") if isinstance(profile.get("specialties"), list) else [],
        "units": profile.get("units") if isinstance(profile.get("units"), list) else [],
        "professionals": profile.get("professionals") if isinstance(profile.get("professionals"), list) else [],
        "technologies": profile.get("technologies") if isinstance(profile.get("technologies"), list) else [],
        "locations": profile.get("locations") if isinstance(profile.get("locations"), list) else [],
        "contact": {
            key: value
            for key, value in {
                "emails": emails,
                "phones": phones,
                "instagram": instagram,
            }.items()
            if value
        },
        "recommendation_context": recommendation_context(input_data, final_url),
        "source_job_id": clean_str(job.get("id")),
        "review_only": True,
    }
    return {key: value for key, value in candidate.items() if value not in ("", [], {})}


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    candidate = as_dict(result.get("candidate"))
    compact = {
        key: result.get(key)
        for key in (
            "job_id",
            "status",
            "source_url",
            "writes_data",
            "reason",
            "completed_job",
        )
        if result.get(key) not in (None, "", [], {})
    }
    if candidate:
        compact["candidate"] = {
            key: candidate.get(key)
            for key in ("name", "website", "city", "country", "discovery_confidence")
            if candidate.get(key)
        }
        counts = compact_profile_counts(candidate)
        if counts:
            compact["candidate"]["field_counts"] = counts
        context = as_dict(candidate.get("recommendation_context"))
        if context:
            compact["candidate"]["recommendation_context"] = {
                key: context.get(key)
                for key in ("source", "requested_info_label", "allowed_output")
                if context.get(key)
            }
    return compact


def validate_job(job: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if clean_str(job.get("job_type")) != JOB_TYPE:
        raise ValueError("job is not DISCOVER_CLINIC")
    input_data = as_dict(job.get("input"))
    source_url = first_source_url(input_data)
    return input_data, source_url


def process_job(
    job: dict[str, Any],
    args: argparse.Namespace,
    admin_email: str,
    local_env: dict[str, str],
    fetcher: Callable[..., Any] = fetch_url,
    completer: Callable[..., dict[str, Any]] = complete_job,
) -> dict[str, Any]:
    input_data, source_url = validate_job(job)
    job_id = clean_str(job.get("id"))
    if not source_url:
        return {
            "job_id": job_id,
            "status": "needs_search_provider",
            "reason": "No official URL is present. Keep queued until a real discovery/search provider is available.",
            "writes_data": False,
        }

    extraction = extract_from_fetch(fetcher(source_url, timeout=args.timeout))
    candidate = build_candidate(job, extraction, source_url)
    result: dict[str, Any] = {
        "job_id": job_id,
        "status": "ready",
        "source_url": candidate.get("source_url") or source_url,
        "candidate": candidate,
        "writes_data": False,
    }

    if args.apply:
        note = clean_str(
            "Fuente oficial procesada desde recomendación. "
            + requested_info_label(input_data)
            + (". Nota: " + operator_note(input_data) if operator_note(input_data) else "")
        )
        completed = completer(
            job_id,
            [candidate],
            admin_email,
            note,
            candidate.get("discovery_confidence"),
            0,
            local_env,
        )
        result["completed_job"] = {
            "status": completed.get("status"),
            "review_items_created": completed.get("review_items_created"),
            "duplicate_review_items_created": completed.get("duplicate_review_items_created"),
        }
        result["writes_data"] = True
    return result


def pick_next_source_job(admin_email: str, worker: str, local_env: dict[str, str]) -> dict[str, Any] | None:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
target as (
  select j.id
  from public.agent_jobs j
  cross join claims
  where public.is_admin()
    and j.status = 'queued'
    and j.scheduled_for <= now()
    and j.job_type = {sql_literal(JOB_TYPE)}
    and (
      nullif(btrim(coalesce(j.input ->> 'source_url', '')), '') ~* '^https?://'
      or nullif(btrim(coalesce(j.input ->> 'official_url', '')), '') ~* '^https?://'
      or nullif(btrim(coalesce(j.input ->> 'website', '')), '') ~* '^https?://'
      or nullif(btrim(coalesce(j.input ->> 'web', '')), '') ~* '^https?://'
      or exists (
        select 1
        from jsonb_array_elements_text(
          case
            when jsonb_typeof(coalesce(j.input -> 'source_urls', '[]'::jsonb)) = 'array'
              then coalesce(j.input -> 'source_urls', '[]'::jsonb)
            else '[]'::jsonb
          end
        ) as source_item(url)
        where source_item.url ~* '^https?://'
      )
    )
  order by j.priority asc, j.scheduled_for asc, j.created_at asc
  for update skip locked
  limit 1
),
updated as (
  update public.agent_jobs j
  set
    status = 'running',
    attempts = attempts + 1,
    locked_by = {sql_literal(worker)},
    started_at = now(),
    finished_at = null,
    error_message = null
  from target
  where j.id = target.id
  returning j.*
),
event as (
  insert into public.change_events (
    event_name,
    actor_type,
    actor_id,
    entity_type,
    entity_id,
    payload
  )
  select
    'source_backed_discovery_job_picked',
    'admin',
    lower({sql_literal(admin_email)}),
    'agent_job',
    updated.id,
    jsonb_build_object('worker', {sql_literal(worker)})
  from updated
)
select coalesce((select to_jsonb(updated.*) from updated), 'null'::jsonb);
"""
    output = run_psql(sql, local_env).strip()
    if not output or output == "null":
        return None
    return json.loads(output)


def peek_next_source_job(local_env: dict[str, str]) -> dict[str, Any] | None:
    sql = f"""
select to_jsonb(j)
from public.agent_jobs j
where j.status = 'queued'
  and j.scheduled_for <= now()
  and j.job_type = {sql_literal(JOB_TYPE)}
  and (
    nullif(btrim(coalesce(j.input ->> 'source_url', '')), '') ~* '^https?://'
    or nullif(btrim(coalesce(j.input ->> 'official_url', '')), '') ~* '^https?://'
    or nullif(btrim(coalesce(j.input ->> 'website', '')), '') ~* '^https?://'
    or nullif(btrim(coalesce(j.input ->> 'web', '')), '') ~* '^https?://'
    or exists (
      select 1
      from jsonb_array_elements_text(
        case
          when jsonb_typeof(coalesce(j.input -> 'source_urls', '[]'::jsonb)) = 'array'
            then coalesce(j.input -> 'source_urls', '[]'::jsonb)
          else '[]'::jsonb
        end
      ) as source_item(url)
      where source_item.url ~* '^https?://'
    )
  )
order by j.priority asc, j.scheduled_for asc, j.created_at asc
limit 1;
"""
    output = run_psql(sql, local_env).strip()
    if not output or output == "null":
        return None
    return json.loads(output)


def fail_discovery_job(job_id: str, error: str, admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
)
select to_jsonb(public.admin_fail_agent_job({sql_literal(job_id)}::uuid, {sql_literal(error)}::text))
from claims;
"""
    output = run_psql(sql, local_env).strip()
    return json.loads(output) if output else {}


def load_job_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("--job-json must contain one job object.")
    return data


def synthetic_job_from_url(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "id": "local-source-recommendation",
        "job_type": JOB_TYPE,
        "input": {
            "mode": "shadow",
            "source": "local_url_test",
            "source_url": args.url,
            "clinic_name": args.clinic_name,
            "city": args.city,
            "country": args.country,
            "requested_info_label": args.requested_info,
            "operator_note": args.note,
            "allowed_output": "review_queue_proposal_only",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pick-next", action="store_true", help="Process the next queued source-backed DISCOVER_CLINIC job.")
    source.add_argument("--job-json", type=Path, help="Process a saved job JSON locally without database writes.")
    source.add_argument("--url", help="Dry-run one official URL without reading or writing Supabase.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--admin-email", help="Admin email used for assignment/audit.")
    parser.add_argument("--worker", default=WORKER_NAME)
    parser.add_argument("--clinic-name", default="")
    parser.add_argument("--city", default="")
    parser.add_argument("--country", default="España")
    parser.add_argument("--requested-info", default="Recomendación de clínica")
    parser.add_argument("--note", default="")
    parser.add_argument("--apply", action="store_true", help="Complete the picked job and create review_queue items. Never edits or publishes clinics.")
    parser.add_argument("--compact", action="store_true", help="Print counts and routing context without raw proposal details.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.apply and not args.pick_next:
        raise SystemExit("--apply is only allowed with --pick-next so the job lifecycle stays consistent.")

    local_env = load_env_file()
    admin_email = args.admin_email or (get_default_admin_email(local_env) if args.apply else "local-shadow@example.test")
    if args.job_json:
        job = load_job_json(args.job_json)
    elif args.url:
        job = synthetic_job_from_url(args)
    else:
        job = pick_next_source_job(admin_email, args.worker, local_env) if args.apply else peek_next_source_job(local_env)
        if not job:
            print(json.dumps({"status": "empty", "reason": "No queued source-backed discovery jobs."}, ensure_ascii=False))
            return 0

    try:
        result = process_job(job, args, admin_email, local_env)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        if args.apply and clean_str(job.get("id")):
            fail_discovery_job(clean_str(job.get("id")), str(error), admin_email, local_env)
        raise SystemExit(str(error))
    print(json.dumps(compact_result(result) if args.compact else result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
