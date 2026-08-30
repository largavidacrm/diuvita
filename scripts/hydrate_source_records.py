#!/usr/bin/env python3
"""Hydrate Supabase source_records with compact source evidence.

For each pending source URL, this fetches the page and stores title, hash,
retrieval metadata and a short text excerpt. It does not store full pages and
does not change clinic profiles.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError

from capture_source_snapshot import fetch_url, snapshot_from_fetch
from source_snapshot_records import insert_source_snapshot_sql, snapshot_storage_path
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


HYDRATOR_NAME = "vitalarga-source-hydrator"
HYDRATOR_VERSION = "2026-08-30"


def sql_json(value: Any) -> str:
    return sql_literal(json.dumps(value, ensure_ascii=False)) + "::jsonb"


def first_json_line(output: str) -> Any:
    for line in output.splitlines():
        clean = line.strip()
        if clean.startswith("{") or clean.startswith("["):
            return json.loads(clean)
    raise ValueError("No JSON row returned by psql.")


def fetch_pending_sources(
    limit: int,
    refresh: bool,
    retry_errors: bool,
    local_env: dict[str, str],
) -> list[dict[str, Any]]:
    pending_filter = "true" if refresh else """
    (
      sr.content_hash is null
      or (
        sr.raw_excerpt is null
        and coalesce((sr.metadata ->> 'text_excerpt_empty')::boolean, false) = false
      )
      or sr.source_title is null
      or sr.metadata ->> 'text_sha256' is null
    )
"""
    error_filter = "true" if refresh or retry_errors else """
    (
      sr.metadata ->> 'last_hydration_error_at' is null
      or (sr.metadata ->> 'last_hydration_error_at')::timestamptz < now() - interval '24 hours'
    )
"""
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.created_at asc), '[]'::jsonb)
from (
  select
    sr.id,
    sr.clinic_id,
    sr.entity_type,
    sr.entity_id,
    sr.source_url,
    sr.metadata,
    sr.created_at
  from public.source_records sr
  where sr.source_url ~* '^https?://'
    and {pending_filter}
    and {error_filter}
  order by sr.created_at asc
  limit {int(limit)}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def snapshot_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "hydrated_by": HYDRATOR_NAME,
        "hydrator_version": HYDRATOR_VERSION,
        "hydrated_at": snapshot.get("retrieved_at"),
        "final_url": snapshot.get("final_url"),
        "http_status": snapshot.get("http_status"),
        "content_type": snapshot.get("content_type"),
        "request_profile": snapshot.get("request_profile"),
        "content_length": snapshot.get("content_length"),
        "text_sha256": snapshot.get("text_sha256"),
        "text_excerpt_empty": not bool(snapshot.get("text_excerpt")),
    }


def update_source_record_sql(record_id: str, snapshot: dict[str, Any]) -> str:
    return f"""
update public.source_records
set
  source_title = coalesce({sql_literal(snapshot.get("source_title"))}, source_title),
  retrieved_at = coalesce({sql_literal(snapshot.get("retrieved_at"))}::timestamptz, retrieved_at),
  content_hash = {sql_literal(snapshot.get("content_sha256"))},
  snapshot_storage_path = {sql_literal(snapshot_storage_path(snapshot))},
  raw_excerpt = {sql_literal(snapshot.get("text_excerpt"))},
  metadata = coalesce(metadata, '{{}}'::jsonb) || {sql_json(snapshot_metadata(snapshot))}
where id = {sql_literal(record_id)}::uuid
returning jsonb_build_object(
  'id', id,
  'source_url', source_url,
  'content_hash', content_hash,
  'snapshot_storage_path', snapshot_storage_path,
  'has_excerpt', raw_excerpt is not null
);
"""


def record_failure_sql(record_id: str, source_url: str, error: str) -> str:
    return f"""
update public.source_records
set metadata = coalesce(metadata, '{{}}'::jsonb) || jsonb_build_object(
  'last_hydration_error_at', now(),
  'last_hydration_error', left({sql_literal(error)}, 500),
  'last_hydration_source_url', {sql_literal(source_url)},
  'hydrated_by', {sql_literal(HYDRATOR_NAME)},
  'hydrator_version', {sql_literal(HYDRATOR_VERSION)}
)
where id = {sql_literal(record_id)}::uuid
returning jsonb_build_object(
  'id', id,
  'source_url', source_url,
  'error_recorded', true
);
"""


def hydrate_record(record: dict[str, Any], args: argparse.Namespace, local_env: dict[str, str]) -> dict[str, Any]:
    source_url = str(record.get("source_url") or "")
    try:
        snapshot = snapshot_from_fetch(
            fetch_url(source_url, timeout=args.timeout),
            excerpt_chars=args.excerpt_chars,
        )
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
        recorded = None
        if args.apply and record.get("id"):
            recorded = first_json_line(run_psql(record_failure_sql(str(record["id"]), source_url, str(error)), local_env))
        return {
            "id": record.get("id"),
            "source_url": source_url,
            "status": "failed",
            "error": str(error),
            "recorded": recorded,
        }

    if not args.apply:
        return {
            "id": record.get("id"),
            "source_url": source_url,
            "status": "ready",
            "title": snapshot.get("source_title"),
            "hash": str(snapshot.get("content_sha256") or "")[:12],
            "excerpt_chars": len(snapshot.get("text_excerpt") or ""),
        }

    updated = first_json_line(run_psql(update_source_record_sql(str(record["id"]), snapshot), local_env))
    snapshot_row = first_json_line(run_psql(
        insert_source_snapshot_sql(record, snapshot, HYDRATOR_NAME, HYDRATOR_VERSION),
        local_env,
    ))
    return {
        "id": record.get("id"),
        "source_url": source_url,
        "status": "updated",
        "updated": updated,
        "snapshot": snapshot_row,
    }


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    updated = item.get("updated") if isinstance(item.get("updated"), dict) else {}
    return {
        "id": item.get("id"),
        "source_url": item.get("source_url"),
        "status": item.get("status"),
        "title": item.get("title"),
        "excerpt_chars": item.get("excerpt_chars"),
        "has_excerpt": updated.get("has_excerpt"),
        "error": item.get("error"),
    }


def compact_output(output: dict[str, Any]) -> dict[str, Any]:
    items = output.get("items") if isinstance(output.get("items"), list) else []
    compact_items = [compact_item(item) for item in items if isinstance(item, dict)]
    return {
        "mode": output.get("mode"),
        "sources_seen": output.get("sources_seen"),
        "ready_or_updated": output.get("ready_or_updated"),
        "failed": output.get("failed"),
        "items": compact_items,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--excerpt-chars", type=int, default=1600)
    parser.add_argument("--refresh", action="store_true", help="Refresh already hydrated records too.")
    parser.add_argument("--retry-errors", action="store_true", help="Retry sources that failed hydration recently.")
    parser.add_argument("--apply", action="store_true", help="Update Supabase source_records.")
    parser.add_argument("--compact", action="store_true", help="Print compact output without snapshot details.")
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
    records = fetch_pending_sources(args.limit, args.refresh, args.retry_errors, local_env)
    results = [hydrate_record(record, args, local_env) for record in records]
    output = {
        "mode": "apply" if args.apply else "dry_run",
        "sources_seen": len(records),
        "ready_or_updated": sum(1 for item in results if item["status"] in {"ready", "updated"}),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "items": results,
    }
    if args.compact:
        output = compact_output(output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
