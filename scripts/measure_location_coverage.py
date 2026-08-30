#!/usr/bin/env python3
"""Read-only location coverage report for visible Vitalarga clinic profiles."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import as_int, parse_timestamp, plural
from google_maps_url_rules import coalesced_jsonb_text_sql, google_maps_profile_url_sql
from submit_discovery_candidates import load_env_file, run_psql


def safe_limit(value: int) -> int:
    return max(1, min(100, int(value)))


def load_location_coverage(limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    capped_limit = safe_limit(limit)
    location_maps_check = google_maps_profile_url_sql(
        coalesced_jsonb_text_sql("location.value", ("maps_url", "google_maps_url", "map_url"))
    )
    sql = f"""
with visible_clinics as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city as clinic_city,
    c.status,
    c.current_data
  from public.clinics c
  where c.status in ('published', 'preliminary')
),
location_rows as (
  select
    c.id,
    c.slug,
    c.clinic_name,
    c.clinic_city,
    c.status,
    location.ordinality as location_index,
    coalesce(
      nullif(btrim(coalesce(location.value ->> 'name', location.value ->> 'nombre', '')), ''),
      nullif(btrim(coalesce(location.value ->> 'city', location.value ->> 'ciudad', '')), ''),
      case when location.ordinality = 1 then 'Sede principal' else 'Sede adicional' end
    ) as location_label,
    nullif(btrim(coalesce(
      location.value ->> 'address',
      location.value ->> 'direccion',
      location.value ->> 'dirección',
      case
        when jsonb_typeof(location.value) = 'string'
          then location.value #>> '{{}}'
        else ''
      end
    )), '') is not null as has_address,
    {location_maps_check} as has_google_maps_profile,
    nullif(btrim(coalesce(
      location.value ->> 'google_reviews_url',
      location.value ->> 'reviews_url',
      location.value ->> 'valoraciones_url',
      ''
    )), '') is not null as has_google_reviews
  from visible_clinics c
  cross join lateral jsonb_array_elements(
    case
      when jsonb_typeof(c.current_data -> 'locations') = 'array'
        then c.current_data -> 'locations'
      else '[]'::jsonb
    end
  ) with ordinality as location(value, ordinality)
),
location_checks as (
  select
    lr.*,
    count(*) over (partition by lr.id) as clinic_location_count,
    array_remove(array[
      case when not has_address then 'Dirección' end,
      case when not has_google_maps_profile then 'Google Maps de clínica' end,
      case when not has_google_reviews then 'Valoraciones Google' end
    ], null) as pending_fields
  from location_rows lr
),
summary as (
  select jsonb_build_object(
    'visible_clinics', (select count(*) from visible_clinics),
    'clinics_with_locations', count(distinct id),
    'multi_location_clinics', count(distinct id) filter (where clinic_location_count > 1),
    'total_locations', count(*),
    'locations_with_address', count(*) filter (where has_address),
    'locations_missing_address', count(*) filter (where not has_address),
    'locations_with_google_maps_profile', count(*) filter (where has_google_maps_profile),
    'locations_missing_google_maps_profile', count(*) filter (where not has_google_maps_profile),
    'locations_with_google_reviews', count(*) filter (where has_google_reviews),
    'locations_missing_google_reviews', count(*) filter (where not has_google_reviews)
  ) as data
  from location_checks
),
pending_locations as (
  select coalesce(
    jsonb_agg(
      to_jsonb(items)
      order by items.pending_count desc,
        items.clinic_location_count desc,
        case when items.status = 'published' then 0 else 1 end,
        items.clinic_name,
        items.location_index
    ),
    '[]'::jsonb
  ) as data
  from (
    select
      slug,
      clinic_name,
      clinic_city,
      status,
      location_index,
      location_label,
      clinic_location_count,
      pending_fields,
      coalesce(array_length(pending_fields, 1), 0) as pending_count
    from location_checks
    where coalesce(array_length(pending_fields, 1), 0) > 0
    order by pending_count desc,
      clinic_location_count desc,
      case when status = 'published' then 0 else 1 end,
      clinic_name,
      location_index
    limit {capped_limit}
  ) items
),
next_location_target as (
  select coalesce(
    (
      select to_jsonb(items)
      from (
        select
          slug,
          clinic_name,
          clinic_city,
          status,
          location_index,
          location_label,
          clinic_location_count,
          pending_fields,
          coalesce(array_length(pending_fields, 1), 0) as pending_count
        from location_checks
        where coalesce(array_length(pending_fields, 1), 0) > 0
        order by pending_count desc,
          clinic_location_count desc,
          case when status = 'published' then 0 else 1 end,
          clinic_name,
          location_index
        limit 1
      ) items
    ),
    '{{}}'::jsonb
  ) as data
)
select jsonb_build_object(
  'summary', (select data from summary),
  'pending_locations', (select data from pending_locations),
  'next_location_target', (select data from next_location_target),
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
    if not denominator:
        return "0%"
    return f"{round((numerator / denominator) * 100)}%"


def location_name(row: dict[str, Any]) -> str:
    label = str(row.get("location_label") or "").strip()
    if label:
        return label
    return "Sede principal" if as_int(row.get("location_index")) <= 1 else "Sede adicional"


def next_location_action(report: dict[str, Any]) -> str:
    target = report.get("next_location_target") or {}
    if not isinstance(target, dict) or not target:
        return "sin sedes pendientes medidas"
    clinic = str(target.get("clinic_name") or target.get("slug") or "la primera clínica")
    location = location_name(target)
    pending = [str(item) for item in target.get("pending_fields") or [] if str(item).strip()]
    if pending:
        return f"Revisar {location} de {clinic}: pendiente {', '.join(pending)}"
    return f"Revisar sedes de {clinic}"


def format_location_row(row: dict[str, Any]) -> str:
    clinic = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("clinic_city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    location = location_name(row)
    location_count = as_int(row.get("clinic_location_count"))
    pending = ", ".join(str(item) for item in row.get("pending_fields") or [])
    location_note = f"{location_count} {plural(location_count, 'sede', 'sedes')}" if location_count else "sede"
    return f"- {clinic} · {city} · {status} · {location} · {location_note} · pendiente: {pending}"


def format_location_coverage(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    total_locations = as_int(summary.get("total_locations"))
    maps_ready = as_int(summary.get("locations_with_google_maps_profile"))
    reviews_ready = as_int(summary.get("locations_with_google_reviews"))
    address_ready = as_int(summary.get("locations_with_address"))
    rows = report.get("pending_locations") or []
    lines = [
        "# Vitalarga location coverage",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        "",
        "## Resumen",
        f"- Clínicas visibles: {as_int(summary.get('visible_clinics'))}",
        f"- Clínicas con sedes explícitas: {as_int(summary.get('clinics_with_locations'))}",
        f"- Clínicas con varias sedes: {as_int(summary.get('multi_location_clinics'))}",
        f"- Sedes medidas: {total_locations}",
        f"- Sedes con dirección: {address_ready}/{total_locations} ({pct(address_ready, total_locations)})",
        f"- Sedes con Google Maps de clínica: {maps_ready}/{total_locations} ({pct(maps_ready, total_locations)})",
        f"- Sedes con valoraciones Google: {reviews_ready}/{total_locations} ({pct(reviews_ready, total_locations)})",
        "- Writes data: no",
        "",
        "## Siguiente acción",
        f"- {next_location_action(report)}",
        "",
        "## Sedes con campos pendientes",
    ]
    if not rows:
        lines.append("- No hay sedes explícitas con campos pendientes medidos.")
    for row in rows:
        lines.append(format_location_row(row))
    lines.append("")
    lines.append("Nota: este informe no publica, no edita clínicas y no ordena clínicas por calidad.")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = load_location_coverage(safe_limit(args.limit), load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_location_coverage(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
