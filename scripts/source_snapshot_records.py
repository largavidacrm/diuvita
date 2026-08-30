#!/usr/bin/env python3
"""SQL helpers for durable compact source snapshots."""
from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from capture_source_snapshot import safe_host
from submit_discovery_candidates import sql_literal


SNAPSHOT_SCHEMA_VERSION = "2026-08-30"


def sql_json(value: Any) -> str:
    return sql_literal(json.dumps(value, ensure_ascii=False)) + "::jsonb"


def uuid_sql(value: Any) -> str:
    return "null::uuid" if value in (None, "") else sql_literal(value) + "::uuid"


def snapshot_storage_path(snapshot: dict[str, Any]) -> str:
    retrieved = str(snapshot.get("retrieved_at") or "unknown-date")
    year = retrieved[:4] if len(retrieved) >= 4 else "unknown-year"
    month = retrieved[5:7] if len(retrieved) >= 7 else "unknown-month"
    digest = str(snapshot.get("content_sha256") or "nohash")[:16]
    host = safe_host(str(snapshot.get("final_url") or snapshot.get("source_url") or "unknown"))
    return str(PurePosixPath("source_snapshots") / year / month / host / f"{digest}.json")


def snapshot_metadata(
    snapshot: dict[str, Any],
    observed_by: str,
    observed_version: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "observed_by": observed_by,
        "observed_version": observed_version,
        "observed_at": snapshot.get("retrieved_at"),
        "text_excerpt_empty": not bool(snapshot.get("text_excerpt")),
    }
    if extra:
        metadata.update(extra)
    return metadata


def insert_source_snapshot_sql(
    record: dict[str, Any],
    snapshot: dict[str, Any],
    observed_by: str,
    observed_version: str,
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    record_id = str(record.get("id") or record.get("source_record_id") or "")
    metadata = snapshot_metadata(snapshot, observed_by, observed_version, extra_metadata)
    return f"""
insert into public.source_snapshots (
  source_record_id,
  clinic_id,
  entity_type,
  entity_id,
  source_url,
  final_url,
  source_title,
  retrieved_at,
  http_status,
  content_type,
  content_length,
  content_hash,
  text_hash,
  snapshot_storage_path,
  text_excerpt,
  metadata
)
select
  sr.id,
  coalesce({uuid_sql(record.get("clinic_id"))}, sr.clinic_id),
  coalesce({sql_literal(record.get("entity_type"))}, sr.entity_type, 'clinic'),
  coalesce({uuid_sql(record.get("entity_id"))}, sr.entity_id),
  coalesce({sql_literal(snapshot.get("source_url"))}, sr.source_url),
  {sql_literal(snapshot.get("final_url"))},
  {sql_literal(snapshot.get("source_title"))},
  coalesce({sql_literal(snapshot.get("retrieved_at"))}::timestamptz, now()),
  {sql_literal(snapshot.get("http_status"))}::integer,
  {sql_literal(snapshot.get("content_type"))},
  {sql_literal(snapshot.get("content_length"))}::integer,
  {sql_literal(snapshot.get("content_sha256"))},
  {sql_literal(snapshot.get("text_sha256"))},
  {sql_literal(snapshot_storage_path(snapshot))},
  {sql_literal(snapshot.get("text_excerpt"))},
  {sql_json(metadata)}
from public.source_records sr
where sr.id = {sql_literal(record_id)}::uuid
on conflict (source_record_id, content_hash, (coalesce(text_hash, ''))) do update
set
  retrieved_at = excluded.retrieved_at,
  source_title = coalesce(excluded.source_title, public.source_snapshots.source_title),
  snapshot_storage_path = excluded.snapshot_storage_path,
  text_excerpt = coalesce(excluded.text_excerpt, public.source_snapshots.text_excerpt),
  metadata = public.source_snapshots.metadata || excluded.metadata
returning jsonb_build_object(
  'id', id,
  'source_record_id', source_record_id,
  'content_hash', content_hash,
  'text_hash', text_hash,
  'snapshot_storage_path', snapshot_storage_path
);
"""
