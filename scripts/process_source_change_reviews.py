#!/usr/bin/env python3
"""Turn source-change review cards into profile-enrichment proposals.

Default mode is dry-run. Apply mode creates internal review cards only; it does
not resolve the source-change card, edit clinic data or publish pages.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError

from capture_source_snapshot import fetch_url
from extract_clinic_profile_shadow import extract_from_fetch
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal
from submit_shadow_extraction_review import create_review, review_payload
from verify_clinic_profile_shadow import verify_extraction


PROCESSOR_NAME = "vitalarga-source-change-processor"
PROCESSOR_VERSION = "2026-08-30"


def load_source_change_reviews(limit: int, review_id: str | None, local_env: dict[str, str]) -> list[dict[str, Any]]:
    review_filter = f"and rq.id = {sql_literal(review_id)}::uuid" if review_id else ""
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.created_at asc), '[]'::jsonb)
from (
  select
    rq.id,
    rq.clinic_id,
    rq.title,
    rq.payload,
    rq.created_at
  from public.review_queue rq
  where rq.status = 'open'
    and rq.review_type = 'source_change_detected'
    {review_filter}
  order by rq.created_at asc
  limit {max(1, min(100, int(limit)))}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def source_change_input(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    return {
        "review_id": row.get("id"),
        "clinic_id": row.get("clinic_id"),
        "clinic_slug": payload.get("clinic_slug"),
        "clinic_name": payload.get("clinic_name"),
        "source_url": payload.get("source_url"),
        "material_hints": payload.get("material_hints") if isinstance(payload.get("material_hints"), list) else [],
        "material_summary": payload.get("material_summary") or "Contenido general",
    }


def enrichment_payload_for_change(change: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    payload = review_payload(str(change.get("clinic_slug") or ""), verification)
    warnings = list(payload.get("warnings") or [])
    warnings.insert(0, "Fuente vigilada modificada; revisar propuesta antes de guardar.")
    payload.update({
        "processor": PROCESSOR_NAME,
        "processor_version": PROCESSOR_VERSION,
        "source_change_review_id": change.get("review_id"),
        "source_change_material_hints": change.get("material_hints") or [],
        "source_change_material_summary": change.get("material_summary"),
        "warnings": warnings,
    })
    return payload


def process_review(row: dict[str, Any], args: argparse.Namespace, admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    change = source_change_input(row)
    if not change.get("clinic_slug") or not change.get("source_url"):
        return {
            "review_id": change.get("review_id"),
            "status": "skipped",
            "reason": "source-change review is missing clinic_slug or source_url",
        }

    try:
        extraction = extract_from_fetch(fetch_url(str(change["source_url"]), timeout=args.timeout))
        verification = verify_extraction(extraction)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return {
            "review_id": change.get("review_id"),
            "clinic_slug": change.get("clinic_slug"),
            "source_url": change.get("source_url"),
            "status": "failed",
            "error": str(error),
        }

    payload = enrichment_payload_for_change(change, verification)
    proposed_fields = payload.get("proposed_fields") or {}
    result = {
        "review_id": change.get("review_id"),
        "clinic_slug": change.get("clinic_slug"),
        "source_url": change.get("source_url"),
        "status": "ready" if proposed_fields else "empty",
        "material_summary": change.get("material_summary"),
        "proposed_fields": sorted(proposed_fields.keys()),
        "verification_summary": payload.get("verification_summary") or {},
    }
    if args.apply and proposed_fields:
        result["created_review"] = create_review(
            str(change["clinic_slug"]),
            payload,
            admin_email,
            local_env,
            replace_existing=True,
        )
    return result


def summarize_results(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "reviews_seen": len(results),
        "ready": sum(1 for item in results if item.get("status") == "ready"),
        "empty": sum(1 for item in results if item.get("status") == "empty"),
        "skipped": sum(1 for item in results if item.get("status") == "skipped"),
        "failed": sum(1 for item in results if item.get("status") == "failed"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--review-id", help="Process one source_change_detected review card.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--admin-email", help="Admin email assigned to created review cards.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create internal clinic_profile_enrichment review cards. Never publishes or edits clinics.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    rows = load_source_change_reviews(args.limit, args.review_id, local_env)
    results = [process_review(row, args, admin_email, local_env) for row in rows]
    output = {
        "mode": "apply" if args.apply else "dry_run",
        **summarize_results(results),
        "items": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
