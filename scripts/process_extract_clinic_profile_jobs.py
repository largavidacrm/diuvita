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
CreateReviewFn = Callable[[str, dict[str, Any], str, dict[str, str], bool, bool, bool], dict[str, Any]]
ResolveOriginReviewFn = Callable[[dict[str, Any], dict[str, Any], str, dict[str, str]], dict[str, Any] | None]
OriginReviewFollowupFn = Callable[[dict[str, Any], dict[str, Any] | None, dict[str, Any], str, dict[str, str]], dict[str, Any] | None]


REQUESTED_FIELD_TARGETS = {
    "summary": {"summary"},
    "resumen": {"summary"},
    "address": {"locations"},
    "location": {"locations"},
    "locations": {"locations"},
    "maps_url": {"locations"},
    "google_maps_url": {"locations"},
    "care_mode": {"care_mode"},
    "modality": {"care_mode"},
    "modalidad": {"care_mode"},
    "online": {"care_mode", "locations"},
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
    "clinic_registry_number": {"clinic_registry_number"},
    "registry": {"clinic_registry_number"},
    "regcess": {"clinic_registry_number"},
    "professional_license_numbers": {"professional_license_numbers"},
    "license": {"professional_license_numbers", "team_credentialing_visible"},
    "colegiacion": {"professional_license_numbers", "team_credentialing_visible"},
    "public_pricing": {"public_pricing"},
    "pricing_url": {"public_pricing", "pricing_url"},
    "visit_price": {"visit_price", "public_pricing", "pricing_url"},
    "price": {"visit_price", "public_pricing", "pricing_url"},
    "precio": {"visit_price", "public_pricing", "pricing_url"},
}

SOURCE_JOB_REVIEW_HANDOFF_ROUTES = {
    "manual_review_banner_source_handoff",
    "review_card_specialist_source_handoff",
}
SOURCE_JOB_REVIEW_HANDOFF_SCOPES = {
    "primary_target_first",
    "specialist_source_only",
}
REVIEW_REPLACED_STATUSES = {"inserted", "updated", "updated_clinic"}
QUALITY_ISSUE_TARGETS = {
    "missing_website": {"website"},
    "weak_summary": {"summary"},
    "missing_services": {"services"},
    "missing_specialties": {"specialties"},
    "missing_units": {"unidades"},
    "missing_professionals": {"profesionales"},
    "missing_technology": {"tech"},
    "missing_address": {"address", "locations"},
    "missing_contact": {"email", "telefono", "phone_fixed", "phone_mobile", "phone_whatsapp", "instagram"},
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
    return clean_string_list(input_data.get("requested_fields"))


def clean_string_list(value: Any) -> list[str]:
    fields = [clean_str(item) for item in as_list(value)]
    return [item for item in fields if item]


def primary_requested_fields(input_data: dict[str, Any], fields: list[str]) -> list[str]:
    primary = clean_string_list(input_data.get("primary_requested_fields"))
    if primary:
        return primary
    if clean_str(input_data.get("target_scope")) == "primary_target_first" and fields:
        return fields[:1]
    return []


def primary_requested_field_labels(input_data: dict[str, Any], primary_fields: list[str]) -> list[str]:
    labels = clean_string_list(input_data.get("primary_requested_field_labels"))
    if labels:
        return labels
    requested_labels = clean_string_list(input_data.get("requested_field_labels"))
    if primary_fields and requested_labels:
        return requested_labels[: len(primary_fields)]
    return []


def requested_targets(fields: list[str]) -> set[str]:
    targets: set[str] = set()
    for field in fields:
        targets.update(REQUESTED_FIELD_TARGETS.get(field, {field}))
    return targets


def source_job_handled_fields(job: dict[str, Any], fields: list[str]) -> list[str]:
    input_data = as_dict(job.get("input"))
    primary_fields = primary_requested_fields(input_data, fields)
    if clean_str(input_data.get("target_scope")) == "primary_target_first" and primary_fields:
        return primary_fields
    return fields


def quality_issue_code(issue: Any) -> str:
    if isinstance(issue, dict):
        return clean_str(issue.get("code")).lower()
    return ""


def quality_issue_text(issue: Any) -> str:
    if isinstance(issue, dict):
        return " ".join(
            clean_str(issue.get(key)).lower()
            for key in ("code", "label", "detail", "reason")
            if clean_str(issue.get(key))
        )
    return clean_str(issue).lower()


def quality_issue_targets(issue: Any) -> set[str]:
    code = quality_issue_code(issue)
    if code in QUALITY_ISSUE_TARGETS:
        return set(QUALITY_ISSUE_TARGETS[code])
    text = quality_issue_text(issue)
    targets: set[str] = set()
    if "summary" in text or "resumen" in text:
        targets.add("summary")
    if "website" in text or "web" in text:
        targets.add("website")
    if "address" in text or "direcci" in text or "sede" in text:
        targets.update({"address", "locations"})
    if "contact" in text or "contacto" in text or "tel" in text or "email" in text:
        targets.update(QUALITY_ISSUE_TARGETS["missing_contact"])
    if "service" in text or "servicio" in text:
        targets.add("services")
    if "specialt" in text or "especialidad" in text:
        targets.add("specialties")
    if "unit" in text or "unidad" in text:
        targets.add("unidades")
    if "professional" in text or "profesional" in text or "specialist" in text or "especialista" in text:
        targets.add("profesionales")
    if "technology" in text or "tecnolog" in text:
        targets.add("tech")
    return targets


def quality_issue_matches_fields(issue: Any, fields: list[str]) -> bool:
    target_fields = requested_targets(fields)
    return bool(target_fields and quality_issue_targets(issue).intersection(target_fields))


def split_quality_issues_for_source_job(
    origin_review: dict[str, Any],
    job: dict[str, Any],
) -> tuple[list[Any], list[Any]]:
    payload = as_dict(origin_review.get("payload"))
    issues = as_list(payload.get("issues"))
    if len(issues) <= 1:
        return issues, []
    handled_fields = source_job_handled_fields(job, requested_fields(as_dict(job.get("input"))))
    handled: list[Any] = []
    remaining: list[Any] = []
    for issue in issues:
        if quality_issue_matches_fields(issue, handled_fields):
            handled.append(issue)
        else:
            remaining.append(issue)
    if not handled:
        return [], issues
    return handled, remaining


def issue_identity(issue: Any) -> str:
    if isinstance(issue, dict):
        code = clean_str(issue.get("code")).lower()
        if code:
            return "code:" + code
    return "text:" + quality_issue_text(issue)


def merge_quality_issues(existing: list[Any], additional: list[Any]) -> list[Any]:
    merged: list[Any] = []
    seen: set[str] = set()
    for issue in existing + additional:
        identity = issue_identity(issue)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        merged.append(issue)
    return merged


def source_job_origin_review_id(job: dict[str, Any]) -> str:
    return clean_str(as_dict(job.get("input")).get("from_review_id"))


def review_source_job_should_replace_existing_reviews(job: dict[str, Any]) -> bool:
    input_data = as_dict(job.get("input"))
    return (
        bool(source_job_origin_review_id(job))
        and clean_str(input_data.get("ui_route")) in SOURCE_JOB_REVIEW_HANDOFF_ROUTES
        and clean_str(input_data.get("target_scope")) in SOURCE_JOB_REVIEW_HANDOFF_SCOPES
        and clean_str(input_data.get("allowed_output") or "review_queue_proposal_only") == "review_queue_proposal_only"
    )


def created_review_replaces_origin(created_review: dict[str, Any] | None) -> bool:
    return clean_str(as_dict(created_review).get("status")) in REVIEW_REPLACED_STATUSES


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
    primary_fields = primary_requested_fields(input_data, fields)
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
        "primary_requested_fields": primary_fields,
        "primary_requested_field_labels": primary_requested_field_labels(input_data, primary_fields),
        "operator_requested_field_keys": clean_string_list(
            input_data.get("operator_requested_field_keys") or input_data.get("requested_fields")
        ),
        "operator_requested_field_labels": clean_string_list(
            input_data.get("operator_requested_field_labels") or input_data.get("requested_field_labels")
        ),
        "operator_requested_field_summary": clean_str(input_data.get("operator_requested_field_summary")),
        "target_scope": clean_str(input_data.get("target_scope")),
        "ui_route": clean_str(input_data.get("ui_route")),
        "missing_fields": [clean_str(item) for item in as_list(input_data.get("missing_fields")) if clean_str(item)],
        "human_supplied_source": bool(input_data.get("human_supplied_source")),
        "source_job_version": clean_str(input_data.get("source_job_version")),
        "operator_intent": clean_str(input_data.get("operator_intent")),
        "llm_boundary": clean_str(input_data.get("llm_boundary") or "respect_source_job_context_scope"),
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
    origin_review_resolver: ResolveOriginReviewFn | None = None,
    origin_review_followup: OriginReviewFollowupFn | None = None,
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
        "primary_requested_fields": payload.get("primary_requested_fields") or [],
        "target_scope": payload.get("target_scope") or "",
        "ui_route": payload.get("ui_route") or "",
        "missing_fields": payload.get("missing_fields") or [],
        "status": "ready" if proposed_fields else "empty",
        "proposed_fields": sorted(proposed_fields.keys()),
        "proposed_field_counts": proposed_field_counts(proposed_fields),
        "verification_summary": payload.get("verification_summary") or {},
        "quality_warnings": payload.get("warnings") or [],
        "writes_data": False,
    }
    if args.apply and proposed_fields:
        source_replaces_review = review_source_job_should_replace_existing_reviews(job)
        result["created_review"] = review_creator(
            clinic_slug,
            payload,
            admin_email,
            local_env,
            args.replace_existing or source_replaces_review,
            args.allow_multiple_open_clinic_reviews,
            source_replaces_review,
        )
        if source_replaces_review and created_review_replaces_origin(result.get("created_review")):
            followup = origin_review_followup or handle_origin_review_after_source_job
            result["origin_review_followup"] = followup(
                job,
                result.get("created_review"),
                result,
                admin_email,
                local_env,
            )
            resolver = origin_review_resolver or supersede_origin_review
            result["superseded_review"] = resolver(job, result["created_review"], admin_email, local_env)
        result["writes_data"] = True
    elif args.apply and review_source_job_should_replace_existing_reviews(job):
        followup = origin_review_followup or handle_origin_review_after_source_job
        result["origin_review_followup"] = followup(job, None, result, admin_email, local_env)
        result["writes_data"] = bool(result.get("origin_review_followup"))
    return result


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": result.get("job_id"),
        "clinic_slug": result.get("clinic_slug"),
        "clinic_name": result.get("clinic_name"),
        "source_url": result.get("source_url"),
        "requested_fields": result.get("requested_fields") or [],
        "primary_requested_fields": result.get("primary_requested_fields") or [],
        "target_scope": result.get("target_scope") or "",
        "ui_route": result.get("ui_route") or "",
        "missing_fields": result.get("missing_fields") or [],
        "status": result.get("status"),
        "proposed_fields": result.get("proposed_fields") or [],
        "proposed_field_counts": result.get("proposed_field_counts") or {},
        "quality_warnings": result.get("quality_warnings") or [],
        "created_review": result.get("created_review"),
        "superseded_review": result.get("superseded_review"),
        "origin_review_followup": result.get("origin_review_followup"),
        "writes_data": bool(result.get("writes_data")),
    }


def supersede_origin_review(
    job: dict[str, Any],
    created_review: dict[str, Any],
    admin_email: str,
    local_env: dict[str, str],
) -> dict[str, Any] | None:
    origin_review_id = source_job_origin_review_id(job)
    if not origin_review_id:
        return None
    created_review_id = clean_str(as_dict(created_review).get("id"))
    created_review_title = clean_str(as_dict(created_review).get("title"))
    note_parts = [
        "Sustituida por propuesta concreta generada desde la URL oficial indicada por Daniel.",
        "No publica datos ni modifica la ficha.",
    ]
    if created_review_title:
        note_parts.append(f"Propuesta revisable: {created_review_title}.")
    if created_review_id:
        note_parts.append(f"review_id nuevo/actualizado: {created_review_id}.")
    note = " ".join(note_parts)
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
open_origin as (
  select rq.id
  from public.review_queue rq
  where rq.id = {sql_literal(origin_review_id)}::uuid
    and rq.status = 'open'
)
select to_jsonb(public.admin_resolve_review_item(
  {sql_literal(origin_review_id)}::uuid,
  'resolved',
  {sql_literal(note)}::text
))
from claims
cross join open_origin;
"""
    output = run_psql(sql, local_env).strip()
    return json.loads(output) if output else None


def sql_uuid(value: Any) -> str:
    clean = clean_str(value)
    return f"{sql_literal(clean)}::uuid" if clean else "null"


def run_json_sql(sql: str, local_env: dict[str, str]) -> Any:
    output = run_psql(sql, local_env).strip()
    if not output or output == "null":
        return None
    return json.loads(output)


def load_review_by_id(review_id: str, local_env: dict[str, str]) -> dict[str, Any] | None:
    if not review_id:
        return None
    sql = f"""
select to_jsonb(rq)
from public.review_queue rq
where rq.id = {sql_literal(review_id)}::uuid;
"""
    row = run_json_sql(sql, local_env)
    return row if isinstance(row, dict) else None


def load_open_quality_followup_review(
    clinic_id: str,
    origin_review_id: str,
    local_env: dict[str, str],
) -> dict[str, Any] | None:
    if not clinic_id:
        return None
    sql = f"""
select to_jsonb(rq)
from public.review_queue rq
where rq.clinic_id = {sql_literal(clinic_id)}::uuid
  and rq.id <> {sql_literal(origin_review_id)}::uuid
  and rq.status = 'open'
  and rq.review_type = 'clinic_quality_audit'
  and coalesce(rq.payload ->> 'quality_context', '') <> 'blocking_claims'
order by rq.created_at asc
limit 1;
"""
    row = run_json_sql(sql, local_env)
    return row if isinstance(row, dict) else None


def source_handoff_field_labels(job: dict[str, Any], fields: list[str]) -> list[str]:
    input_data = as_dict(job.get("input"))
    primary_fields = primary_requested_fields(input_data, requested_fields(input_data))
    if clean_str(input_data.get("target_scope")) == "primary_target_first" and primary_fields:
        labels = primary_requested_field_labels(input_data, primary_fields)
        return labels or primary_fields
    labels = clean_string_list(input_data.get("requested_field_labels"))
    return labels[: len(fields)] if labels else fields


def source_handoff_progress(
    job: dict[str, Any],
    created_review: dict[str, Any] | None,
    result: dict[str, Any],
    status: str,
    handled_issues: list[Any] | None = None,
    remaining_issues: list[Any] | None = None,
) -> dict[str, Any]:
    input_data = as_dict(job.get("input"))
    fields = source_job_handled_fields(job, requested_fields(input_data))
    return {
        "status": status,
        "job_id": job.get("id"),
        "source_url": first_url(input_data),
        "handled_fields": fields,
        "handled_field_labels": source_handoff_field_labels(job, fields),
        "requested_fields": requested_fields(input_data),
        "requested_field_labels": clean_string_list(input_data.get("requested_field_labels")),
        "target_scope": clean_str(input_data.get("target_scope")),
        "ui_route": clean_str(input_data.get("ui_route")),
        "created_review_id": clean_str(as_dict(created_review).get("id")),
        "created_review_title": clean_str(as_dict(created_review).get("title")),
        "proposed_fields": result.get("proposed_fields") or [],
        "handled_issues": [clean_str(as_dict(issue).get("label")) or clean_str(issue) for issue in handled_issues or []],
        "remaining_issue_count": len(remaining_issues or []),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def followup_quality_title(origin_review: dict[str, Any]) -> str:
    title = clean_str(origin_review.get("title"))
    if title.lower().startswith("completar ficha:"):
        return "Revisión manual:" + title.split(":", 1)[1]
    if title:
        return title
    payload = as_dict(origin_review.get("payload"))
    clinic_name = clean_str(payload.get("clinic_name"))
    return f"Revisión manual: {clinic_name}" if clinic_name else "Revisión manual de ficha"


def quality_review_payload_with_handoff(
    base_payload: dict[str, Any],
    issues: list[Any],
    progress: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(base_payload)
    payload["issues"] = issues
    manual_progress = as_dict(payload.get("manual_review_progress"))
    manual_progress["source_handoff"] = progress
    payload["manual_review_progress"] = manual_progress
    return payload


def write_json_change_event(
    event_name: str,
    entity_type: str,
    entity_id: str,
    clinic_id: str,
    payload: dict[str, Any],
    admin_email: str,
    local_env: dict[str, str],
) -> None:
    payload_json = json.dumps(payload, ensure_ascii=False)
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
)
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
  {sql_literal(event_name)},
  'admin',
  lower({sql_literal(admin_email)}),
  {sql_literal(entity_type)},
  {sql_uuid(entity_id)},
  {sql_uuid(clinic_id)},
  {sql_literal(payload_json)}::jsonb
from claims;
"""
    run_psql(sql, local_env)


def upsert_remaining_quality_review(
    origin_review: dict[str, Any],
    job: dict[str, Any],
    created_review: dict[str, Any],
    result: dict[str, Any],
    handled_issues: list[Any],
    remaining_issues: list[Any],
    admin_email: str,
    local_env: dict[str, str],
) -> dict[str, Any] | None:
    clinic_id = clean_str(origin_review.get("clinic_id")) or clean_str(as_dict(origin_review.get("payload")).get("clinic_id"))
    origin_review_id = clean_str(origin_review.get("id"))
    if not clinic_id or clean_str(origin_review.get("status")) == "dismissed":
        return None
    existing = load_open_quality_followup_review(clinic_id, origin_review_id, local_env)
    progress = source_handoff_progress(
        job,
        created_review,
        result,
        "remaining_manual_review_preserved",
        handled_issues,
        remaining_issues,
    )
    if existing:
        existing_payload = as_dict(existing.get("payload"))
        merged_issues = merge_quality_issues(as_list(existing_payload.get("issues")), remaining_issues)
        payload = quality_review_payload_with_handoff(existing_payload, merged_issues, progress)
        payload_json = json.dumps(payload, ensure_ascii=False)
        sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
updated as (
  update public.review_queue rq
  set
    payload = {sql_literal(payload_json)}::jsonb,
    priority = greatest(rq.priority, {int(origin_review.get("priority") or 0)})
  where rq.id = {sql_literal(clean_str(existing.get("id")))}::uuid
    and exists (select 1 from claims)
  returning *
)
select to_jsonb(updated) from updated;
"""
        row = run_json_sql(sql, local_env)
        status = "updated" if row else "missing"
        followup_id = clean_str(as_dict(row).get("id"))
    else:
        payload = quality_review_payload_with_handoff(as_dict(origin_review.get("payload")), remaining_issues, progress)
        payload_json = json.dumps(payload, ensure_ascii=False)
        sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
inserted as (
  insert into public.review_queue (
    job_id,
    clinic_id,
    review_type,
    title,
    priority,
    status,
    payload
  )
  select
    {sql_uuid(origin_review.get("job_id"))},
    {sql_uuid(clinic_id)},
    'clinic_quality_audit',
    {sql_literal(followup_quality_title(origin_review))},
    {int(origin_review.get("priority") or 85)},
    'open',
    {sql_literal(payload_json)}::jsonb
  from claims
  returning *
)
select to_jsonb(inserted) from inserted;
"""
        row = run_json_sql(sql, local_env)
        status = "inserted" if row else "missing"
        followup_id = clean_str(as_dict(row).get("id"))
    if followup_id:
        write_json_change_event(
            "manual_quality_review_preserved_after_source_handoff",
            "review_queue",
            followup_id,
            clinic_id,
            {
                "origin_review_id": origin_review_id,
                "source_job_id": job.get("id"),
                "created_review_id": clean_str(as_dict(created_review).get("id")),
                "remaining_issue_count": len(remaining_issues),
                "handled_issue_count": len(handled_issues),
            },
            admin_email,
            local_env,
        )
    return {
        "status": status,
        "id": followup_id,
        "origin_review_id": origin_review_id,
        "remaining_issue_count": len(remaining_issues),
        "handled_issue_count": len(handled_issues),
    }


def reopen_origin_review_after_empty_source_job(
    origin_review: dict[str, Any],
    job: dict[str, Any],
    result: dict[str, Any],
    admin_email: str,
    local_env: dict[str, str],
) -> dict[str, Any] | None:
    origin_review_id = clean_str(origin_review.get("id"))
    clinic_id = clean_str(origin_review.get("clinic_id")) or clean_str(as_dict(origin_review.get("payload")).get("clinic_id"))
    if not origin_review_id or clean_str(origin_review.get("status")) == "dismissed":
        return None
    progress = source_handoff_progress(job, None, result, "no_proposal_returned")
    payload = dict(as_dict(origin_review.get("payload")))
    payload["source_handoff_progress"] = progress
    payload_json = json.dumps(payload, ensure_ascii=False)
    resolution = dict(as_dict(origin_review.get("resolution")))
    resolution["source_handoff_result"] = progress
    resolution_json = json.dumps(resolution, ensure_ascii=False)
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
updated as (
  update public.review_queue rq
  set
    status = 'open',
    payload = {sql_literal(payload_json)}::jsonb,
    resolution = {sql_literal(resolution_json)}::jsonb,
    resolved_by = null,
    resolved_at = null
  where rq.id = {sql_literal(origin_review_id)}::uuid
    and rq.status <> 'dismissed'
    and exists (select 1 from claims)
  returning *
)
select to_jsonb(updated) from updated;
"""
    row = run_json_sql(sql, local_env)
    if not row:
        return None
    write_json_change_event(
        "manual_review_reopened_after_empty_source_job",
        "review_queue",
        origin_review_id,
        clinic_id,
        {
            "source_job_id": job.get("id"),
            "source_url": progress.get("source_url"),
            "handled_fields": progress.get("handled_fields"),
        },
        admin_email,
        local_env,
    )
    return {
        "status": "reopened",
        "id": clean_str(as_dict(row).get("id")),
        "origin_review_id": origin_review_id,
    }


def handle_origin_review_after_source_job(
    job: dict[str, Any],
    created_review: dict[str, Any] | None,
    result: dict[str, Any],
    admin_email: str,
    local_env: dict[str, str],
) -> dict[str, Any] | None:
    origin_review = load_review_by_id(source_job_origin_review_id(job), local_env)
    if not origin_review:
        return None
    if clean_str(result.get("status")) == "empty":
        return reopen_origin_review_after_empty_source_job(origin_review, job, result, admin_email, local_env)
    if clean_str(origin_review.get("review_type")) != "clinic_quality_audit":
        return None
    if as_dict(origin_review.get("payload")).get("quality_context") == "blocking_claims":
        return None
    handled_issues, remaining_issues = split_quality_issues_for_source_job(origin_review, job)
    if not remaining_issues:
        return None
    return upsert_remaining_quality_review(
        origin_review,
        job,
        as_dict(created_review),
        result,
        handled_issues,
        remaining_issues,
        admin_email,
        local_env,
    )


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
    lower({sql_literal(admin_email)}),
    'agent_job',
    updated.id,
    updated.clinic_id,
    jsonb_build_object(
      'mode', 'shadow',
      'review_created', {sql_literal(str(bool(output.get("created_review"))).lower())}::boolean,
      'origin_review_superseded', {sql_literal(str(bool(output.get("superseded_review"))).lower())}::boolean,
      'proposed_fields', {sql_literal(json.dumps(output.get("proposed_fields") or [], ensure_ascii=False))}::jsonb
    )
  from updated
  cross join claims
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
