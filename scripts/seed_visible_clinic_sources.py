#!/usr/bin/env python3
"""Seed official website source_records for visible clinics.

This is an internal provenance helper. It only stores a clinic's already-known
official website as a source record when that same host is not already stored.
It does not edit clinic profiles, create claims, resolve reviews or publish.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import parse_timestamp
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


SEEDER_NAME = "vitalarga-official-source-seeder"
SEEDER_VERSION = "2026-08-30"


def safe_limit(value: int) -> int:
    return max(1, min(100, int(value)))


def source_metadata() -> dict[str, Any]:
    return {
        "seeded_by": SEEDER_NAME,
        "seeder_version": SEEDER_VERSION,
        "reason": "visible_clinic_existing_official_website",
        "profile_fields_changed": False,
        "requires_human_review": False,
    }


def seed_candidates_sql(limit: int) -> str:
    capped_limit = safe_limit(limit)
    return f"""
with candidates as (
  select
    c.id as clinic_id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.country,
    c.status,
    c.website,
    public.normalized_url_host(c.website) as website_host
  from public.clinics c
  where c.status in ('published', 'preliminary')
    and c.website ~* '^https?://'
    and public.normalized_url_host(c.website) is not null
    and not exists (
      select 1
      from public.source_records sr
      where sr.clinic_id = c.id
        and sr.entity_type = 'clinic'
        and public.normalized_url_host(sr.source_url) = public.normalized_url_host(c.website)
    )
  order by
    case when c.status = 'published' then 0 else 1 end,
    c.display_name
  limit {capped_limit}
)
select coalesce(jsonb_agg(to_jsonb(candidates)), '[]'::jsonb)
from candidates;
"""


def insert_sources_sql(limit: int) -> str:
    capped_limit = safe_limit(limit)
    metadata_json = json.dumps(source_metadata(), ensure_ascii=False)
    return f"""
with candidates as (
  select
    c.id as clinic_id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.country,
    c.status,
    c.website,
    public.normalized_url_host(c.website) as website_host
  from public.clinics c
  where c.status in ('published', 'preliminary')
    and c.website ~* '^https?://'
    and public.normalized_url_host(c.website) is not null
    and not exists (
      select 1
      from public.source_records sr
      where sr.clinic_id = c.id
        and sr.entity_type = 'clinic'
        and public.normalized_url_host(sr.source_url) = public.normalized_url_host(c.website)
    )
  order by
    case when c.status = 'published' then 0 else 1 end,
    c.display_name
  limit {capped_limit}
),
inserted as (
  insert into public.source_records (
    clinic_id,
    entity_type,
    entity_id,
    source_url,
    source_title,
    source_type,
    retrieved_at,
    metadata
  )
  select
    clinic_id,
    'clinic',
    clinic_id,
    website,
    clinic_name || ' · web oficial',
    'official_website',
    now(),
    {sql_literal(metadata_json)}::jsonb
  from candidates
  returning
    id,
    clinic_id,
    source_url,
    source_title,
    source_type,
    retrieved_at,
    metadata
),
inserted_rows as (
  select
    i.id,
    i.clinic_id,
    c.slug,
    c.clinic_name,
    c.city,
    c.country,
    c.status,
    c.website,
    i.source_url,
    i.source_title,
    i.source_type,
    i.retrieved_at,
    i.metadata
  from inserted i
  join candidates c on c.clinic_id = i.clinic_id and c.website = i.source_url
)
select jsonb_build_object(
  'inserted', coalesce(jsonb_agg(to_jsonb(inserted_rows) order by inserted_rows.clinic_name), '[]'::jsonb),
  'inserted_count', count(*),
  'generated_at', now()
)
from inserted_rows;
"""


def load_seed_candidates(limit: int, local_env: dict[str, str]) -> list[dict[str, Any]]:
    return json.loads(run_psql(seed_candidates_sql(limit), local_env) or "[]")


def apply_seed(limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    return json.loads(run_psql(insert_sources_sql(limit), local_env) or "{}")


def format_seed_row(row: dict[str, Any]) -> str:
    name = row.get("clinic_name") or row.get("source_title") or "sin nombre"
    city = row.get("city") or "-"
    status = row.get("status") or "-"
    url = row.get("website") or row.get("source_url") or "-"
    return f"- {name} · {city} · {status} · {url}"


def format_report(
    *,
    candidates: list[dict[str, Any]],
    apply: bool,
    result: dict[str, Any] | None = None,
) -> str:
    inserted = []
    if isinstance(result, dict):
        raw_inserted = result.get("inserted") or []
        if isinstance(raw_inserted, list):
            inserted = raw_inserted
    rows = inserted if apply else candidates
    generated_at = result.get("generated_at") if isinstance(result, dict) else None
    output = [
        "# Vitalarga: siembra de fuentes oficiales",
        "",
        f"Generado: {parse_timestamp(generated_at)}",
        f"- Writes data: {'yes' if apply else 'no'}",
        f"- Fuentes candidatas: {len(candidates)}",
    ]
    if apply:
        output.append(f"- Fuentes guardadas: {len(inserted)}")
    output.extend([
        "",
        "## Clínicas",
    ])
    if not rows:
        output.append("- No hay webs oficiales pendientes de guardar como fuente interna.")
    for row in rows:
        output.append(format_seed_row(row))
    output.extend([
        "",
        "Nota: no edita fichas, no crea claims, no resuelve revisiones y no publica la web.",
    ])
    return "\n".join(output) + "\n"


def json_report(
    *,
    candidates: list[dict[str, Any]],
    apply: bool,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inserted = []
    if isinstance(result, dict) and isinstance(result.get("inserted"), list):
        inserted = result["inserted"]
    return {
        "mode": "apply" if apply else "dry_run",
        "writes_data": apply,
        "candidates_seen": len(candidates),
        "inserted_count": len(inserted),
        "items": inserted if apply else candidates,
        "generated_at": result.get("generated_at") if isinstance(result, dict) else None,
        "safety": "does not edit clinics, create claims, resolve reviews or publish",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--apply", action="store_true", help="Write source_records to Supabase.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    local_env = load_env_file()
    candidates = load_seed_candidates(args.limit, local_env)
    result = apply_seed(args.limit, local_env) if args.apply else None
    if args.json:
        print(json.dumps(
            json_report(candidates=candidates, apply=args.apply, result=result),
            ensure_ascii=False,
            indent=2,
        ))
    else:
        print(format_report(candidates=candidates, apply=args.apply, result=result), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
