#!/usr/bin/env python3
"""Detect changed clinic source pages in shadow mode.

The watcher compares the latest fetched hash with the stored source_records
hash. It can create internal review cards, but never edits public clinic data.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError

from capture_source_snapshot import fetch_url, snapshot_from_fetch
from source_snapshot_records import insert_source_snapshot_sql
from submit_discovery_candidates import get_default_admin_email, load_env_file, run_psql, sql_literal


WATCHER_NAME = "vitalarga-source-watcher"
WATCHER_VERSION = "2026-08-30"
MATERIAL_HINTS = {
    "contact": {
        "label": "Contacto",
        "terms": ("telefono", "whatsapp", "email", "correo", "direccion", "contacto", "horario", "cita"),
    },
    "team": {
        "label": "Equipo",
        "terms": ("doctor", "doctora", "dra", "dr.", "equipo", "medico", "medica", "especialista", "profesional"),
    },
    "services": {
        "label": "Servicios",
        "terms": ("servicio", "programa", "unidad", "diagnostico", "tratamiento", "terapia", "medicina preventiva", "longevidad"),
    },
    "prices": {
        "label": "Precios",
        "terms": ("precio", "tarifa", "cuota", "consulta inicial", "€", "eur", "euro"),
    },
    "medical_claims": {
        "label": "Claims médicos",
        "terms": ("cura", "curar", "revierte", "revertir", "rejuvenece", "antiaging", "anti-aging", "resultado", "garantia", "garantiza"),
    },
}


DEFAULT_MONITOR_CADENCE_DAYS = 30
MIN_MONITOR_CADENCE_DAYS = 7
MAX_MONITOR_CADENCE_DAYS = 90


def fetch_sources(pool_limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    sql = f"""
select coalesce(jsonb_agg(to_jsonb(items) order by items.last_checked_at asc nulls first), '[]'::jsonb)
from (
  select
    sr.id,
    sr.clinic_id,
    sr.source_url,
    sr.source_title,
    sr.retrieved_at,
    sr.content_hash,
    sr.raw_excerpt,
    sr.metadata,
    sr.source_type,
    latest.latest_snapshot_at,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city as clinic_city,
    c.country as clinic_country,
    c.status as clinic_status,
    coalesce(latest.latest_snapshot_at, sr.retrieved_at) as last_checked_at
  from public.source_records sr
  join public.clinics c on c.id = sr.clinic_id
  left join lateral (
    select max(ss.retrieved_at) as latest_snapshot_at
    from public.source_snapshots ss
    where ss.source_record_id = sr.id
  ) latest on true
  where sr.entity_type = 'clinic'
    and sr.content_hash is not null
    and sr.source_url ~* '^https?://'
  order by coalesce(latest.latest_snapshot_at, sr.retrieved_at) asc nulls first
  limit {int(pool_limit)}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def bounded_cadence_days(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        days = int(value)
    except (TypeError, ValueError):
        return None
    return max(MIN_MONITOR_CADENCE_DAYS, min(MAX_MONITOR_CADENCE_DAYS, days))


def monitor_cadence_days(record: dict[str, Any]) -> int:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    explicit = bounded_cadence_days(metadata.get("monitor_cadence_days"))
    if explicit is not None:
        return explicit
    tier = str(metadata.get("monitor_tier") or "").strip().lower()
    if tier in {"weekly", "high", "7", "7d"}:
        return 7
    if tier in {"slow", "low", "90", "90d"}:
        return 90
    return DEFAULT_MONITOR_CADENCE_DAYS


def next_due_at(record: dict[str, Any]) -> datetime | None:
    last_checked = parse_timestamp(record.get("last_checked_at"))
    if last_checked is None:
        return None
    return last_checked + timedelta(days=monitor_cadence_days(record))


def source_due(record: dict[str, Any], now: datetime | None = None) -> bool:
    due_at = next_due_at(record)
    if due_at is None:
        return True
    now = now or datetime.now(timezone.utc)
    return due_at <= now


def select_due_sources(records: list[dict[str, Any]], limit: int, force: bool = False) -> list[dict[str, Any]]:
    selected = records if force else [record for record in records if source_due(record)]
    return selected[:limit]


def normalized_text(value: Any) -> str:
    text = str(value or "").lower()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def material_change_hints(record: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    haystack = normalized_text(" ".join([
        str(record.get("source_title") or ""),
        str(record.get("raw_excerpt") or ""),
        str(metadata.get("text_excerpt") or ""),
        str(snapshot.get("source_title") or ""),
        str(snapshot.get("text_excerpt") or ""),
    ]))
    hints = []
    for area, config in MATERIAL_HINTS.items():
        matches = [term for term in config["terms"] if term in haystack]
        if matches:
            hints.append({
                "area": area,
                "label": config["label"],
                "terms": matches[:4],
            })
    return hints


def material_summary(hints: list[dict[str, Any]]) -> str:
    if not hints:
        return "Contenido general"
    return ", ".join(str(hint.get("label") or hint.get("area")) for hint in hints)


def compare_record(record: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    previous_text_hash = str(metadata.get("text_sha256") or "")
    current_text_hash = str(snapshot.get("text_sha256") or "")
    use_text_hash = bool(previous_text_hash and current_text_hash)
    previous_hash = previous_text_hash if use_text_hash else str(record.get("content_hash") or "")
    current_hash = current_text_hash if use_text_hash else str(snapshot.get("content_sha256") or "")
    changed = bool(previous_hash and current_hash and previous_hash != current_hash)
    hints = material_change_hints(record, snapshot) if changed else []
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
        "material_hints": hints,
        "material_summary": material_summary(hints),
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
        "material_hints": change.get("material_hints"),
        "material_summary": change.get("material_summary"),
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
    snapshot_row = None
    if args.apply:
        snapshot_row = first_json_line(run_psql(
            insert_source_snapshot_sql(
                record,
                snapshot,
                WATCHER_NAME,
                WATCHER_VERSION,
                {"changed": change["changed"], "hash_type": change["hash_type"]},
            ),
            local_env,
        ))
    if not change["changed"]:
        result = {
            "source_record_id": record.get("id"),
            "source_url": record.get("source_url"),
            "clinic_name": record.get("clinic_name"),
            "status": "unchanged",
            "hash": change["current_hash"][:12],
        }
        if snapshot_row:
            result["snapshot"] = snapshot_row
        return result

    result = {
        "source_record_id": record.get("id"),
        "source_url": record.get("source_url"),
        "clinic_name": record.get("clinic_name"),
        "status": "changed",
        "previous_hash": change["previous_hash"][:12],
        "current_hash": change["current_hash"][:12],
        "hash_type": change["hash_type"],
        "material_hints": change["material_hints"],
        "material_summary": change["material_summary"],
    }
    if snapshot_row:
        result["snapshot"] = snapshot_row
    if args.apply:
        result["review"] = first_json_line(run_psql(create_review_sql(change, admin_email), local_env))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--pool-limit", type=int, help="Source candidates to inspect before applying cadence.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--excerpt-chars", type=int, default=1600)
    parser.add_argument("--admin-email", help="Admin email assigned to created review cards.")
    parser.add_argument("--force", action="store_true", help="Ignore monitoring cadence and check the oldest hydrated sources.")
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
    if args.pool_limit is not None and args.pool_limit < args.limit:
        raise SystemExit("--pool-limit must be at least --limit.")

    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    pool_limit = args.pool_limit or max(args.limit * 5, 200)
    candidates = fetch_sources(pool_limit, local_env)
    records = select_due_sources(candidates, args.limit, args.force)
    results = [monitor_record(record, args, admin_email, local_env) for record in records]
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry_run",
                "cadence": "forced" if args.force else "due_only",
                "candidate_sources": len(candidates),
                "due_sources": len(records),
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
