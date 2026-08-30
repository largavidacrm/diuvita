#!/usr/bin/env python3
"""Promote candidate-clinic review cards into internal draft clinics.

Default mode is a dry run. Applying uses the existing Supabase admin function
and creates draft clinics only; it does not publish them.
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


def candidate_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = payload.get("candidate")
    return candidate if isinstance(candidate, dict) else payload


def candidate_confidence(payload: dict[str, Any]) -> float:
    candidate = candidate_from_payload(payload)
    raw = candidate.get("discovery_confidence", candidate.get("confidence"))
    try:
        return max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        return 0.0


def duplicate_probability(payload: dict[str, Any]) -> float:
    try:
        return max(0.0, min(1.0, float(payload.get("duplicate_probability") or 0)))
    except (TypeError, ValueError):
        return 0.0


def classify_review(row: dict[str, Any], min_confidence: float, duplicate_threshold: float) -> dict[str, Any]:
    payload = row.get("payload") or {}
    candidate = candidate_from_payload(payload)
    confidence = candidate_confidence(payload)
    duplicate = duplicate_probability(payload)
    missing = [
        label
        for label, value in [
            ("name", candidate.get("name") or candidate.get("clinic_name")),
            ("city", candidate.get("city")),
            ("country", candidate.get("country") or payload.get("candidate_country")),
        ]
        if not str(value or "").strip()
    ]

    status = "ready"
    reason = "ready_for_internal_draft"
    if duplicate >= duplicate_threshold:
        status = "blocked"
        reason = "probable_duplicate"
    elif missing:
        status = "blocked"
        reason = "missing_" + "_".join(missing)
    elif confidence < min_confidence:
        status = "hold"
        reason = "low_confidence"

    return {
        "review_id": row.get("id"),
        "title": row.get("title"),
        "name": candidate.get("name") or candidate.get("clinic_name"),
        "city": candidate.get("city") or payload.get("candidate_city"),
        "country": candidate.get("country") or payload.get("candidate_country"),
        "website": candidate.get("website") or candidate.get("web") or payload.get("candidate_website"),
        "confidence": confidence,
        "duplicate_probability": duplicate,
        "status": status,
        "reason": reason,
    }


def fetch_reviews(review_id: str | None, limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    review_filter = f"and id = {sql_literal(review_id)}::uuid" if review_id else ""
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.priority desc, items.created_at asc), '[]'::jsonb)
from (
  select
    id,
    title,
    priority,
    payload,
    created_at
  from public.review_queue
  where status = 'open'
    and review_type = 'candidate_clinic'
    {review_filter}
  order by priority desc, created_at asc
  limit {int(limit)}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def promote_review(review_id: str, admin_email: str, note: str, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
with claims as (
  select set_config(
    'request.jwt.claims',
    jsonb_build_object('email', {sql_literal(admin_email)})::text,
    true
  )
),
promoted as (
  select public.admin_create_draft_clinic_from_review(
    {sql_literal(review_id)}::uuid,
    {sql_literal(note)}::text
  ) as clinic
  from claims
)
select jsonb_build_object(
  'review_id', {sql_literal(review_id)},
  'clinic_id', clinic ->> 'id',
  'slug', clinic ->> 'slug',
  'name', clinic ->> 'display_name',
  'status', clinic ->> 'status'
)
from promoted;
"""
    return json.loads(run_psql(sql, local_env))


def dry_run(rows: list[dict[str, Any]], min_confidence: float, duplicate_threshold: float) -> dict[str, Any]:
    items = [classify_review(row, min_confidence, duplicate_threshold) for row in rows]
    return {
        "mode": "dry_run",
        "reviews": len(items),
        "ready": sum(1 for item in items if item["status"] == "ready"),
        "hold": sum(1 for item in items if item["status"] == "hold"),
        "blocked": sum(1 for item in items if item["status"] == "blocked"),
        "items": items,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-id", help="Promote one candidate_clinic review item.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--duplicate-threshold", type=float, default=0.9)
    parser.add_argument("--admin-email", help="Admin email used for audit attribution.")
    parser.add_argument("--apply", action="store_true", help="Create internal draft clinics for ready candidates.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if not 0 <= args.min_confidence <= 1:
        raise SystemExit("--min-confidence must be between 0 and 1.")
    if not 0 <= args.duplicate_threshold <= 1:
        raise SystemExit("--duplicate-threshold must be between 0 and 1.")

    local_env = load_env_file()
    rows = fetch_reviews(args.review_id, args.limit, local_env)
    summary = dry_run(rows, args.min_confidence, args.duplicate_threshold)
    if not args.apply:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    admin_email = args.admin_email or get_default_admin_email(local_env)
    note = "Borrador interno creado desde revisión candidata. No publicado."
    promoted = []
    skipped = []
    by_id = {item["review_id"]: item for item in summary["items"]}
    for row in rows:
        classification = by_id.get(row.get("id"), {})
        if classification.get("status") != "ready":
            skipped.append(classification)
            continue
        promoted.append(promote_review(str(row["id"]), admin_email, note, local_env))

    print(
        json.dumps(
            {
                "mode": "apply",
                "promoted": len(promoted),
                "skipped": len(skipped),
                "drafts": promoted,
                "skipped_items": skipped,
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
