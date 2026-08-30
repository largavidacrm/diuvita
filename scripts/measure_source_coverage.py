#!/usr/bin/env python3
"""Read-only source coverage report for visible Diuvita clinic profiles."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import as_int, parse_timestamp, plural
from submit_discovery_candidates import load_env_file, run_psql


def safe_limit(value: int) -> int:
    return max(1, min(100, int(value)))


def load_source_coverage(limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    capped_limit = safe_limit(limit)
    sql = f"""
with visible_clinics as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.status
  from public.clinics c
  where c.status in ('published', 'preliminary')
),
coverage_rows as (
  select
    c.id,
    c.slug,
    c.clinic_name,
    c.city,
    c.status,
    coalesce(sources.source_records, 0) as source_records,
    coalesce(sources.hydrated_source_records, 0) as hydrated_source_records,
    coalesce(sources.source_snapshots, 0) as source_snapshots,
    sources.last_source_at,
    coalesce(claims.total_claims, 0) as total_claims,
    coalesce(claims.claims_with_source, 0) as claims_with_source,
    coalesce(claims.claims_without_source, 0) as claims_without_source,
    coalesce(claims.blocking_claims, 0) as blocking_claims,
    (
      coalesce(sources.source_records, 0) = 0
      or coalesce(sources.hydrated_source_records, 0) = 0
      or coalesce(claims.total_claims, 0) = 0
      or coalesce(claims.claims_without_source, 0) > 0
      or coalesce(claims.blocking_claims, 0) > 0
    ) as needs_source_work
  from visible_clinics c
  left join lateral (
    select
      count(distinct sr.id) as source_records,
      count(distinct sr.id) filter (where sr.content_hash is not null) as hydrated_source_records,
      count(ss.id) as source_snapshots,
      max(coalesce(ss.retrieved_at, sr.retrieved_at)) as last_source_at
    from public.source_records sr
    left join public.source_snapshots ss on ss.source_record_id = sr.id
    where sr.clinic_id = c.id
      and sr.entity_type = 'clinic'
  ) sources on true
  left join lateral (
    select
      count(*) as total_claims,
      count(*) filter (where fc.source_record_id is not null) as claims_with_source,
      count(*) filter (where fc.source_record_id is null) as claims_without_source,
      count(*) filter (
        where fc.verification_status in ('conflict', 'rejected')
           or fc.source_record_id is null
      ) as blocking_claims
    from public.field_claims fc
    where fc.clinic_id = c.id
      and fc.entity_type = 'clinic'
  ) claims on true
),
summary as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'clinics_with_sources', count(*) filter (where source_records > 0),
    'clinics_without_sources', count(*) filter (where source_records = 0),
    'clinics_with_hydrated_sources', count(*) filter (where hydrated_source_records > 0),
    'clinics_without_hydrated_sources', count(*) filter (where hydrated_source_records = 0),
    'clinics_with_claims', count(*) filter (where total_claims > 0),
    'clinics_without_claims', count(*) filter (where total_claims = 0),
    'clinics_needing_source_work', count(*) filter (where needs_source_work),
    'claims_with_source', coalesce(sum(claims_with_source), 0),
    'claims_without_source', coalesce(sum(claims_without_source), 0),
    'blocking_claims', coalesce(sum(blocking_claims), 0)
  ) as data
  from coverage_rows
),
needs_source_work as (
  select coalesce(
    jsonb_agg(
      to_jsonb(items)
      order by
        items.blocking_claims desc,
        case when items.source_records = 0 then 0 else 1 end,
        case when items.hydrated_source_records = 0 then 0 else 1 end,
        items.claims_without_source desc,
        items.total_claims asc,
        case when items.status = 'published' then 0 else 1 end,
        items.clinic_name
    ),
    '[]'::jsonb
  ) as data
  from (
    select
      slug,
      clinic_name,
      city,
      status,
      source_records,
      hydrated_source_records,
      source_snapshots,
      last_source_at,
      total_claims,
      claims_with_source,
      claims_without_source,
      blocking_claims
    from coverage_rows
    where needs_source_work
    order by
      blocking_claims desc,
      case when source_records = 0 then 0 else 1 end,
      case when hydrated_source_records = 0 then 0 else 1 end,
      claims_without_source desc,
      total_claims asc,
      case when status = 'published' then 0 else 1 end,
      clinic_name
    limit {capped_limit}
  ) items
),
next_source_target as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select
          slug,
          clinic_name,
          city,
          status,
          source_records,
          hydrated_source_records,
          source_snapshots,
          last_source_at,
          total_claims,
          claims_with_source,
          claims_without_source,
          blocking_claims
        from coverage_rows
        where needs_source_work
        order by
          blocking_claims desc,
          case when source_records = 0 then 0 else 1 end,
          case when hydrated_source_records = 0 then 0 else 1 end,
          claims_without_source desc,
          total_claims asc,
          case when status = 'published' then 0 else 1 end,
          clinic_name
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
)
select jsonb_build_object(
  'summary', (select data from summary),
  'needs_source_work', (select data from needs_source_work),
  'next_source_target', (select data from next_source_target),
  'generated_at', now()
);
"""
    return json.loads(run_psql(sql, local_env))


def status_label(status: str) -> str:
    labels = {
        "published": "publicada",
        "preliminary": "preliminar",
    }
    return labels.get(status, status or "-")


def pct(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{round((numerator / denominator) * 100)}%"


def next_source_action(report: dict[str, Any]) -> str:
    target = report.get("next_source_target") or {}
    if not isinstance(target, dict) or not target:
        return "sin hueco de fuentes medido"
    name = str(target.get("clinic_name") or target.get("slug") or "la primera ficha")
    source_records = as_int(target.get("source_records"))
    hydrated = as_int(target.get("hydrated_source_records"))
    total_claims = as_int(target.get("total_claims"))
    without_source = as_int(target.get("claims_without_source"))
    blocking = as_int(target.get("blocking_claims"))
    if not source_records:
        return f"Añadir fuente oficial para {name}"
    if not hydrated:
        return f"Hidratar {source_records} {plural(source_records, 'fuente guardada', 'fuentes guardadas')} de {name}"
    if blocking:
        return f"Revisar {blocking} {plural(blocking, 'claim bloqueante', 'claims bloqueantes')} de {name}"
    if without_source:
        return f"Vincular fuente a {without_source} {plural(without_source, 'claim', 'claims')} de {name}"
    if not total_claims:
        return f"Crear claims internos desde fuentes guardadas para {name}"
    return f"Revisar soporte de fuentes de {name}"


def format_source_row(row: dict[str, Any]) -> str:
    name = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    sources = as_int(row.get("source_records"))
    hydrated = as_int(row.get("hydrated_source_records"))
    snapshots = as_int(row.get("source_snapshots"))
    claims = as_int(row.get("total_claims"))
    claims_with_source = as_int(row.get("claims_with_source"))
    claims_without_source = as_int(row.get("claims_without_source"))
    blocking = as_int(row.get("blocking_claims"))
    return (
        f"- {name} · {city} · {status} · "
        f"fuentes {hydrated}/{sources} hidratadas · "
        f"capturas {snapshots} · "
        f"claims {claims_with_source}/{claims} con fuente"
        + (f" · {claims_without_source} sin fuente" if claims_without_source else "")
        + (f" · {blocking} {plural(blocking, 'bloqueante', 'bloqueantes')}" if blocking else "")
    )


def format_source_coverage(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    visible = as_int(summary.get("visible_clinics"))
    with_sources = as_int(summary.get("clinics_with_sources"))
    hydrated = as_int(summary.get("clinics_with_hydrated_sources"))
    with_claims = as_int(summary.get("clinics_with_claims"))
    needing = as_int(summary.get("clinics_needing_source_work"))
    rows = report.get("needs_source_work") or []
    output = [
        "# Diuvita source coverage",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        "",
        "## Resumen",
        f"- Fichas visibles: {visible}",
        f"- Con fuentes guardadas: {with_sources}/{visible} ({pct(with_sources, visible)})",
        f"- Con fuentes hidratadas: {hydrated}/{visible} ({pct(hydrated, visible)})",
        f"- Con claims internos: {with_claims}/{visible} ({pct(with_claims, visible)})",
        f"- Necesitan trabajo de fuente: {needing}",
        f"- Claims con fuente: {as_int(summary.get('claims_with_source'))}",
        f"- Claims sin fuente: {as_int(summary.get('claims_without_source'))}",
        f"- Claims bloqueantes medidos: {as_int(summary.get('blocking_claims'))}",
        "- Writes data: no",
        "",
        "## Siguiente acción",
        f"- {next_source_action(report)}",
        "",
        "## Fichas que necesitan más soporte de fuente",
    ]
    if not rows:
        output.append("- No hay huecos de fuente medidos en fichas visibles.")
    for row in rows:
        output.append(format_source_row(row))
    output.extend([
        "",
        "Nota: esto no publica, no edita fichas y no decide calidad. Solo mide soporte interno de fuentes.",
    ])
    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_source_coverage(args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_source_coverage(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
