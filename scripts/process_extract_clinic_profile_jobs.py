#!/usr/bin/env python3
"""Process queued EXTRACT_CLINIC_PROFILE jobs into reviewable proposals.

This worker is intentionally conservative. It reads an official source URL from
an internal job, runs the existing shadow extractor/verifier, creates a
clinic_profile_enrichment review card only when useful fields are found, and
never edits or publishes clinic data.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError

from capture_source_snapshot import FetchResult, fetch_url
from extract_clinic_profile_shadow import extract_from_fetch
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal
from submit_shadow_extraction_review import create_review, review_payload
from submit_source_shadow_reviews import proposed_field_counts
from verify_clinic_profile_shadow import verify_extraction


ROOT = Path(__file__).resolve().parents[1]
WORKER_NAME = "review-source-extract-worker"
JOB_TYPE = "EXTRACT_CLINIC_PROFILE"
BATCH_NAME = "review-source-job"
BATCH_VERSION = "2026-08-31"

FetchFn = Callable[..., FetchResult]
CreateReviewFn = Callable[[str, dict[str, Any], str, dict[str, str], bool, bool], dict[str, Any]]


REQUESTED_FIELD_TARGETS = {
    "address": {"locations"},
    "location": {"locations"},
    "locations": {"locations"},
    "maps_url": {"locations"},
    "google_maps_url": {"locations"},
    "contact": {"email", "telefono", "phone_fixed", "phone_mobile", "phone_whatsapp", "instagram"},
    "email": {"email"},
    "telefono": {"telefono", "phone_fixed", "phone_mobile", "phone_whatsapp"},
    "phone": {"telefono", "phone_fixed", "phone_mobile", "phone_whatsapp"},
    "phone_fixed": {"phone_fixed"},
    "phone_mobile": {"phone_mobile"},
    "phone_whatsapp": {"phone_whatsapp"},
    "instagram": {"instagram"},
    "services": {"services"},
    "service": {"services"},
    "specialties": {"specialties"},
    "specialty": {"specialties"},
    "unidades": {"unidades"},
    "units": {"unidades"},
    "unit": {"unidades"},
    "profesionales": {"profesionales"},
    "professionals": {"profesionales"},
    "specialists": {"profesionales"},
    "specialist": {"profesionales"},
    "tech": {"tech"},
    "technology": {"tech"},
    "technologies": {"tech"},
    "years_in_practice": {"years_in_practice"},
    "specialists_count": {"specialists_count"},
    "team_credentialing_visible": {"team_credentialing_visible"},
    "public_pricing": {"public_pricing"},
    "pricing_url": {"public_pricing"},
}


class JobProcessingError(RuntimeError):
    """Expected job processing error that can be recorded on the job."""


def today_batch() -> str:
    return BATCH_NAME + "-" + datetime.now(timezone.utc).date().isoformat()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def clean_str(value: Any) -> str:
    return str(value or "").strip()


def first_url(input_data: dict[str, Any]) -> str:
    url = clean_str(input_data.get("source_url"))
    if url:
        return url
    urls = as_list(input_data.get("source_urls"))
    return clean_str(urls[0]) if urls else ""


def requested_fields(input_data: dict[str, Any]) -> list[str]:
    fields = [clean_str(item) for item in as_list(input_data.get("requested_fields"))]
    return [item for item in fields if item]


def requested_targets(fields: list[str]) -> set[str]:
    targets: set[str] = set()
    for field in fields:
        targets.update(REQUESTED_FIELD_TARGETS.get(field, {field}))
    return targets


def filter_proposed_fields_for_request(
    proposed_fields: dict[str, Any],
    fields: list[str],
) -> dict[str, Any]:
    if not fields:
        return {}
    allowed = requested_targets(fields)
    return {
        key: value
        for key, value in proposed_fields.items()
        if key in allowed
    }


def build_payload_for_job(job: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    input_data = as_dict(job.get("input"))
    clinic_slug = clean_str(input_data.get("clinic_slug"))
    fields = requested_fields(input_data)
    payload = review_payload(clinic_slug, verification)
    payload["proposed_fields"] = filter_proposed_fields_for_request(
        as_dict(payload.get("proposed_fields")),
        fields,
    )
    source_url = first_url(input_data)
    source_urls = [source_url] if source_url else []
    for url in as_list(payload.get("source_urls")):
        clean = clean_str(url)
        if clean and clean not in source_urls:
            source_urls.append(clean)
    warnings = [
        "Fuente indicada desde una revisión; confirmar antes de guardar.",
        "El trabajo solo crea propuestas revisables. No edita la ficha ni publica datos.",
    ]
    warnings.extend(clean_str(item) for item in as_list(payload.get("warnings")) if clean_str(item))
    payload.update({
        "batch": today_batch(),
        "batch_name": BATCH_NAME,
        "batch_version": BATCH_VERSION,
        "job_id": job.get("id"),
        "clinic_id": job.get("clinic_id") or input_data.get("clinic_id"),
        "clinic_slug": clinic_slug,
        "clinic_name": input_data.get("clinic_name"),
        "source_url": source_url,
        "source_urls": source_urls,
        "from_review_id": input_data.get("from_review_id"),
        "requested_fields": fields,
        "requested_field_labels": [
            clean_str(item) for item in as_list(input_data.get("requested_field_labels")) if clean_str(item)
        ],
        "missing_fields": [clean_str(item) for item in as_list(input_data.get("missing_fields")) if clean_str(item)],
        "human_supplied_source": bool(input_data.get("human_supplied_source")),
        "source_job_version": clean_str(input_data.get("source_job_version")),
        "operator_intent": clean_str(input_data.get("operator_intent")),
        "allowed_output": clean_str(input_data.get("allowed_output") or "review_queue_proposal_only"),
        "warnings": warnings,
    })
    return payload


def validate_job(job: dict[str, Any]) -> tuple[str, str, list[str]]:
    if clean_str(job.get("job_type")) != JOB_TYPE:
        raise JobProcessingError("job is not EXTRACT_CLINIC_PROFILE")
    input_data = as_dict(job.get("input"))
    clinic_slug = clean_str(input_data.get("clinic_slug"))
    source_url = first_url(input_data)
    fields = requested_fields(input_data)
    if not clinic_slug:
        raise JobProcessingError("job input is missing clinic_slug")
    if not source_url.startswith(("http://", "https://")):
        raise JobProcessingError("job input is missing a valid source_url")
    if not fields:
        raise JobProcessingError("job input is missing requested_fields")
    return clinic_slug, source_url, fields


def process_job(
    job: dict[str, Any],
    args: argparse.Namespace,
    admin_email: str,
    local_env: dict[str, str],
    fetcher: FetchFn = fetch_url,
    review_creator: CreateReviewFn = create_review,
) -> dict[str, Any]:
    clinic_slug, source_url, fields = validate_job(job)
    extraction = extract_from_fetch(fetcher(source_url, timeout=args.timeout))
    verification = verify_extraction(extraction)
    payload = build_payload_for_job(job, verification)
    proposed_fields = as_dict(payload.get("proposed_fields"))
    result = {
        "job_id": job.get("id"),
        "clinic_id": job.get("clinic_id") or as_dict(job.get("input")).get("clinic_id"),
        "clinic_slug": clinic_slug,
        "clinic_name": as_dict(job.get("input")).get("clinic_name"),
        "source_url": source_url,
        "requested_fields": fields,
        "missing_fields": payload.get("missing_fields") or [],
        "status": "ready" if proposed_fields else "empty",
        "proposed_fields": sorted(proposed_fields.keys()),
        "proposed_field_counts": proposed_field_counts(proposed_fields),
        "verification_summary": payload.get("verification_summary") or {},
        "writes_data": False,
    }
    if args.apply and proposed_fields:
        result["created_review"] = review_creator(
            clinic_slug,
            payload,
            admin_email,
            local_env,
            args.replace_existing,
            args.allow_multiple_open_clinic_reviews,
        )
        result["writes_data"] = True
    return result


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": result.get("job_id"),
        "clinic_slug": result.get("clinic_slug"),
        "clinic_name": result.get("clinic_name"),
        "source_url": result.get("source_url"),
        "requested_fields": result.get("requested_fields") or [],
        "missing_fields": result.get("missing_fields") or [],
        "status": result.get("status"),
        "proposed_fields": result.get("proposed_fields") or [],
        "proposed_field_counts": result.get("proposed_field_counts") or {},
        "created_review": result.get("created_review"),
        "writes_data": bool(result.get("writes_data")),
    }


def pick_next_job(admin_email: str, worker: str, local_env: dict[str, str]) -> dict[str, Any] | None:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
)
select public.admin_pick_agent_job({sql_literal(worker)}, {sql_literal(JOB_TYPE)})
from claims;
"""
    output = run_psql(sql, local_env).strip()
    if not output or output == "null":
        return None
    return json.loads(output)


def peek_next_job(local_env: dict[str, str]) -> dict[str, Any] | None:
    sql = f"""
select to_jsonb(j)
from public.agent_jobs j
where j.status = 'queued'
  and j.scheduled_for <= now()
  and j.job_type = {sql_literal(JOB_TYPE)}
order by j.priority asc, j.scheduled_for asc, j.created_at asc
limit 1;
"""
    output = run_psql(sql, local_env).strip()
    if not output or output == "null":
        return None
    return json.loads(output)


def complete_job(
    job_id: str,
    output: dict[str, Any],
    admin_email: str,
    local_env: dict[str, str],
    confidence: float | None = None,
    cost_cents: int = 0,
) -> dict[str, Any]:
    output_json = json.dumps(output, ensure_ascii=False)
    confidence_sql = "null" if confidence is None else str(max(0, min(1, confidence)))
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
updated as (
  update public.agent_jobs
  set
    status = 'completed',
    output = {sql_literal(output_json)}::jsonb,
    confidence = {confidence_sql}::numeric,
    requires_human = true,
    cost_cents = cost_cents + {max(0, int(cost_cents))},
    locked_by = null,
    started_at = coalesce(started_at, now()),
    finished_at = now(),
    error_message = null
  where id = {sql_literal(job_id)}::uuid
    and job_type = {sql_literal(JOB_TYPE)}
  returning *
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
  select
    'extract_clinic_profile_shadow_completed',
    'admin',
    lower(coalesce((current_setting('request.jwt.claims', true)::jsonb ->> 'email'), '')),
    'agent_job',
    updated.id,
    updated.clinic_id,
    jsonb_build_object(
      'mode', 'shadow',
      'review_created', {sql_literal(str(bool(output.get("created_review"))).lower())}::boolean,
      'proposed_fields', {sql_literal(json.dumps(output.get("proposed_fields") or [], ensure_ascii=False))}::jsonb
    )
  from updated
)
select coalesce((select to_jsonb(updated.*) from updated), 'null'::jsonb);
"""
    completed = run_psql(sql, local_env).strip()
    if not completed or completed == "null":
        raise SystemExit("Could not complete EXTRACT_CLINIC_PROFILE job.")
    return json.loads(completed)


def fail_job(job_id: str, error: str, admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
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
    failed = run_psql(sql, local_env).strip()
    return json.loads(failed) if failed else {}


def load_job_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("--job-json must contain one job object.")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pick-next", action="store_true", help="Process the next queued EXTRACT_CLINIC_PROFILE job.")
    source.add_argument("--job-json", type=Path, help="Process a saved job JSON locally without database writes.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--admin-email", help="Admin email used for assignment/audit.")
    parser.add_argument("--worker", default=WORKER_NAME)
    parser.add_argument("--replace-existing", action="store_true", help="Refresh an existing open review for the same source.")
    parser.add_argument(
        "--allow-multiple-open-clinic-reviews",
        action="store_true",
        help="Allow more than one open enrichment card for the same clinic.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create review cards and mark picked jobs completed. Never edits or publishes clinics.",
    )
    parser.add_argument("--compact", action="store_true", help="Print compact output without verification details.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.apply and args.job_json:
        raise SystemExit("--apply is only allowed with --pick-next so the job lifecycle stays consistent.")

    local_env = load_env_file()
    admin_email = args.admin_email or (get_default_admin_email(local_env) if args.apply else "local-shadow@example.test")
    if args.job_json:
        job = load_job_json(args.job_json)
    elif args.apply:
        job = pick_next_job(admin_email, args.worker, local_env)
    else:
        job = peek_next_job(local_env)

    if not job:
        output = {"mode": "apply" if args.apply else "dry_run", "status": "empty", "job": None}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    try:
        result = process_job(job, args, admin_email, local_env)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError, JobProcessingError) as error:
        if args.apply and job.get("id"):
            fail_job(str(job["id"]), str(error), admin_email, local_env)
        raise SystemExit(str(error))

    if args.apply and job.get("id"):
        complete_job(str(job["id"]), compact_result(result), admin_email, local_env)

    output = {"mode": "apply" if args.apply else "dry_run", "job": compact_result(result) if args.compact else result}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
