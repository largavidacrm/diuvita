#!/usr/bin/env python3
"""Detect changed clinic source pages in shadow mode.

The watcher compares the latest fetched hash with the stored source_records
hash. It can create internal review cards, but never edits public clinic data.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError

from capture_source_snapshot import fetch_url, snapshot_from_fetch
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal


WATCHER_NAME = "diuvita-source-watcher"
WATCHER_VERSION = "2026-08-30"


def fetch_sources(limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.retrieved_at asc), '[]'::jsonb)
from (
  select
    sr.id,
    sr.clinic_id,
    sr.source_url,
    sr.source_title,
    sr.retrieved_at,
    sr.content_hash,
    sr.metadata,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city as clinic_city,
    c.country as clinic_country
  from public.source_records sr
  join public.clinics c on c.id = sr.clinic_id
  where sr.entity_type = 'clinic'
    and sr.content_hash is not null
    and sr.source_url ~* '^https?://'
  order by sr.retrieved_at asc
  limit {int(limit)}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def compare_record(record: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    previous_text_hash = str(metadata.get("text_sha256") or "")
    current_text_hash = str(snapshot.get("text_sha256") or "")
    use_text_hash = bool(previous_text_hash and current_text_hash)
    previous_hash = previous_text_hash if use_text_hash else str(record.get("content_hash") or "")
    current_hash = current_text_hash if use_text_hash else str(snapshot.get("content_sha256") or "")
    changed = bool(previous_hash and current_hash and previous_hash != current_hash)
    return {
        "source_record_id": record.get("id"),
        "clinic_id": record.get("clinic_id"),
        "clinic_slug": record.get("clinic_slug"),
        "clinic_name": record.get("clinic_name"),
        "clinic_city": record.get("clinic_city"),
        "clinic_country": record.get("clinic_country"),
        "source_url": record.get("source_url"),
        "previous_hash": previous_hash,
        "current_hash": current_hash,
        "hash_type": "text" if use_text_hash else "content",
        "changed": changed,
        "source_title": snapshot.get("source_title") or record.get("source_title"),
        "retrieved_at": snapshot.get("retrieved_at"),
        "previous_retrieved_at": record.get("retrieved_at"),
        "excerpt": snapshot.get("text_excerpt"),
    }


def create_review_sql(change: dict[str, Any], admin_email: str) -> str:
    payload = {
        "mode": "shadow",
        "watcher": WATCHER_NAME,
        "watcher_version": WATCHER_VERSION,
        "source_record_id": change.get("source_record_id"),
        "source_url": change.get("source_url"),
        "clinic_slug": change.get("clinic_slug"),
        "clinic_name": change.get("clinic_name"),
        "clinic_city": change.get("clinic_city"),
        "clinic_country": change.get("clinic_country"),
        "previous_hash": change.get("previous_hash"),
        "current_hash": change.get("current_hash"),
        "hash_type": change.get("hash_type"),
        "previous_retrieved_at": change.get("previous_retrieved_at"),
        "retrieved_at": change.get("retrieved_at"),
        "source_title": change.get("source_title"),
        "excerpt": change.get("excerpt"),
    }
    payload_sql = sql_literal(json.dumps(payload, ensure_ascii=False)) + "::jsonb"
    return f"""
with inserted as (
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
    {sql_literal(change["clinic_id"])}::uuid,
    'source_change_detected',
    'Revisar cambio de fuente: ' || {sql_literal(change.get("clinic_name") or "clínica")},
    'source_records',
    70,
    'open',
    {payload_sql},
    {sql_literal(admin_email)}
  where not exists (
    select 1
    from public.review_queue rq
    where rq.review_type = 'source_change_detected'
      and rq.status = 'open'
      and rq.payload ->> 'source_record_id' = {sql_literal(change.get("source_record_id"))}
  )
  returning id, title
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
    'source_change_detected',
    'agent',
    {sql_literal(WATCHER_NAME)},
    'source_record',
    {sql_literal(change["source_record_id"])}::uuid,
    {sql_literal(change["clinic_id"])}::uuid,
    {payload_sql}
  where exists (select 1 from inserted)
  returning id
)
select coalesce(
  (select jsonb_build_object('status', 'inserted', 'id', id, 'title', title) from inserted limit 1),
  jsonb_build_object('status', 'existing')
);
"""


def first_json_line(output: str) -> Any:
    for line in output.splitlines():
        clean = line.strip()
        if clean.startswith("{") or clean.startswith("["):
            return json.loads(clean)
    raise ValueError("No JSON row returned by psql.")


def monitor_record(record: dict[str, Any], args: argparse.Namespace, admin_email: str, local_env: dict[str, str]) -> dict[str, Any]:
    try:
        snapshot = snapshot_from_fetch(
            fetch_url(str(record.get("source_url")), timeout=args.timeout),
            excerpt_chars=args.excerpt_chars,
        )
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        return {
            "source_record_id": record.get("id"),
            "source_url": record.get("source_url"),
            "clinic_name": record.get("clinic_name"),
            "status": "failed",
            "error": str(error),
        }

    change = compare_record(record, snapshot)
    if not change["changed"]:
        return {
            "source_record_id": record.get("id"),
            "source_url": record.get("source_url"),
            "clinic_name": record.get("clinic_name"),
            "status": "unchanged",
            "hash": change["current_hash"][:12],
        }

    result = {
        "source_record_id": record.get("id"),
        "source_url": record.get("source_url"),
        "clinic_name": record.get("clinic_name"),
        "status": "changed",
        "previous_hash": change["previous_hash"][:12],
        "current_hash": change["current_hash"][:12],
        "hash_type": change["hash_type"],
    }
    if args.apply:
        result["review"] = first_json_line(run_psql(create_review_sql(change, admin_email), local_env))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--excerpt-chars", type=int, default=1600)
    parser.add_argument("--admin-email", help="Admin email assigned to created review cards.")
    parser.add_argument("--apply", action="store_true", help="Create source_change_detected review cards.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.excerpt_chars < 200 or args.excerpt_chars > 5000:
        raise SystemExit("--excerpt-chars must be between 200 and 5000.")

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    records = fetch_sources(args.limit, local_env)
    results = [monitor_record(record, args, admin_email, local_env) for record in records]
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry_run",
                "sources_checked": len(results),
                "changed": sum(1 for item in results if item["status"] == "changed"),
                "unchanged": sum(1 for item in results if item["status"] == "unchanged"),
                "failed": sum(1 for item in results if item["status"] == "failed"),
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
