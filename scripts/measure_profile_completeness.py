#!/usr/bin/env python3
"""Read-only completeness report for visible Diuvita clinic profiles."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import as_int, parse_timestamp
from submit_discovery_candidates import load_env_file, run_psql


PUBLIC_STATUSES = ("published", "preliminary")


def safe_limit(value: int) -> int:
    return max(1, min(100, int(value)))


def load_completeness(limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    capped_limit = safe_limit(limit)
    sql = f"""
with clinic_rows as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.status,
    length(btrim(coalesce(c.summary, c.current_data ->> 'summary', ''))) >= 120 as has_summary,
    nullif(btrim(coalesce(c.website, c.current_data ->> 'web', '')), '') is not null as has_website,
    nullif(btrim(coalesce(c.address, c.current_data ->> 'address', '')), '') is not null as has_address,
    nullif(btrim(coalesce(c.current_data ->> 'email', '')), '') is not null as has_email,
    nullif(btrim(coalesce(c.current_data ->> 'telefono', c.current_data ->> 'phone', c.current_data ->> 'telephone', '')), '') is not null as has_phone,
    case
      when jsonb_typeof(c.current_data -> 'services') = 'array'
        then jsonb_array_length(c.current_data -> 'services')
      else 0
    end as services_count,
    case
      when jsonb_typeof(c.current_data -> 'specialties') = 'array'
        then jsonb_array_length(c.current_data -> 'specialties')
      else 0
    end as specialties_count,
    case
      when jsonb_typeof(c.current_data -> 'unidades') = 'array'
        then jsonb_array_length(c.current_data -> 'unidades')
      else 0
    end as units_count,
    case
      when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
        then jsonb_array_length(c.current_data -> 'profesionales')
      else 0
    end as specialists_count,
    case
      when jsonb_typeof(c.current_data -> 'tech') = 'array'
        then jsonb_array_length(c.current_data -> 'tech')
      when nullif(btrim(coalesce(c.current_data ->> 'tech', '')), '') is not null
        then 1
      else 0
    end as technology_count,
    coalesce(reviews.open_quality_reviews, 0) as open_quality_reviews
  from public.clinics c
  left join lateral (
    select count(*) as open_quality_reviews
    from public.review_queue rq
    where rq.clinic_id = c.id
      and rq.status = 'open'
      and rq.review_type = 'clinic_quality_audit'
  ) reviews on true
  where c.status in ('published', 'preliminary')
),
checks as (
  select
    *,
    has_email or has_phone as has_contact,
    services_count > 0 as has_services,
    specialties_count > 0 as has_specialties,
    units_count > 0 as has_units,
    specialists_count > 0 as has_specialists,
    technology_count > 0 as has_technology
  from clinic_rows
),
profile_checks as (
  select
    *,
    array_remove(array[
      case when not has_summary then 'Resumen corto o vacío' end,
      case when not has_website then 'Web oficial' end,
      case when not has_address then 'Dirección' end,
      case when not has_contact then 'Email o teléfono' end,
      case when not has_services then 'Servicios' end,
      case when not has_specialties then 'Especialidades' end,
      case when not has_units then 'Unidades clínicas' end,
      case when not has_specialists then 'Especialistas publicados' end,
      case when not has_technology then 'Tecnología destacada' end
    ], null) as pending_fields
  from checks
),
summary as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'profiles_without_pending_fields', count(*) filter (
      where coalesce(array_length(pending_fields, 1), 0) = 0
    ),
    'profiles_with_pending_fields', count(*) filter (
      where coalesce(array_length(pending_fields, 1), 0) > 0
    ),
    'with_open_quality_reviews', count(*) filter (where open_quality_reviews > 0)
  ) as data
  from profile_checks
),
field_summary as (
  select jsonb_build_array(
    jsonb_build_object('field', 'summary', 'label', 'Resumen suficiente', 'present', count(*) filter (where has_summary), 'pending', count(*) filter (where not has_summary)),
    jsonb_build_object('field', 'website', 'label', 'Web oficial', 'present', count(*) filter (where has_website), 'pending', count(*) filter (where not has_website)),
    jsonb_build_object('field', 'address', 'label', 'Dirección', 'present', count(*) filter (where has_address), 'pending', count(*) filter (where not has_address)),
    jsonb_build_object('field', 'contact', 'label', 'Email o teléfono', 'present', count(*) filter (where has_contact), 'pending', count(*) filter (where not has_contact)),
    jsonb_build_object('field', 'services', 'label', 'Servicios', 'present', count(*) filter (where has_services), 'pending', count(*) filter (where not has_services)),
    jsonb_build_object('field', 'specialties', 'label', 'Especialidades', 'present', count(*) filter (where has_specialties), 'pending', count(*) filter (where not has_specialties)),
    jsonb_build_object('field', 'units', 'label', 'Unidades clínicas', 'present', count(*) filter (where has_units), 'pending', count(*) filter (where not has_units)),
    jsonb_build_object('field', 'specialists', 'label', 'Especialistas publicados', 'present', count(*) filter (where has_specialists), 'pending', count(*) filter (where not has_specialists)),
    jsonb_build_object('field', 'technology', 'label', 'Tecnología destacada', 'present', count(*) filter (where has_technology), 'pending', count(*) filter (where not has_technology))
  ) as data
  from checks
),
pending_profiles as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.status, items.clinic_name), '[]'::jsonb) as data
  from (
    select
      slug,
      clinic_name,
      city,
      status,
      pending_fields,
      coalesce(array_length(pending_fields, 1), 0) as pending_count,
      open_quality_reviews
    from profile_checks
    where coalesce(array_length(pending_fields, 1), 0) > 0
    order by status, clinic_name
    limit {capped_limit}
  ) items
)
select jsonb_build_object(
  'summary', (select data from summary),
  'field_summary', (select data from field_summary),
  'pending_profiles', (select data from pending_profiles),
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


def plural(value: int, singular: str, plural_text: str) -> str:
    return singular if value == 1 else plural_text


def format_pending_profile(row: dict[str, Any]) -> str:
    name = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    pending_fields = row.get("pending_fields") or []
    reviews = as_int(row.get("open_quality_reviews"))
    parts = [
        f"{name} · {city}",
        status,
        "pendiente: " + ", ".join(str(item) for item in pending_fields),
    ]
    if reviews:
        parts.append(f"{reviews} {plural(reviews, 'revisión abierta', 'revisiones abiertas')}")
    return "- " + " · ".join(parts)


def format_completeness(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    visible = as_int(summary.get("visible_clinics"))
    complete = as_int(summary.get("profiles_without_pending_fields"))
    pending_profiles = as_int(summary.get("profiles_with_pending_fields"))
    lines = [
        "# Diuvita profile completeness",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        "",
        "## Resumen",
        f"- Clínicas visibles: {visible}",
        f"- Sin campos pendientes medidos: {complete} ({pct(complete, visible)})",
        f"- Con campos pendientes medidos: {pending_profiles} ({pct(pending_profiles, visible)})",
        f"- Con revisión interna de calidad abierta: {as_int(summary.get('with_open_quality_reviews'))}",
        "- Writes data: no",
        "",
        "## Campos medidos",
    ]

    for field in report.get("field_summary") or []:
        present = as_int(field.get("present"))
        pending = as_int(field.get("pending"))
        lines.append(
            f"- {field.get('label') or field.get('field')}: {present} listos / {pending} pendientes"
        )

    lines.extend(["", "## Fichas con campos pendientes"])
    rows = report.get("pending_profiles") or []
    if not rows:
        lines.append("- No hay fichas visibles con campos pendientes medidos.")
    for row in rows:
        lines.append(format_pending_profile(row))

    lines.extend([
        "",
        "Nota: esto es una medición interna. No publica datos, no cambia fichas y no ordena clínicas por calidad.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_completeness(args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_completeness(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
