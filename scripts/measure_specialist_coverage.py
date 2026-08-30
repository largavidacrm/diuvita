#!/usr/bin/env python3
"""Read-only specialist coverage report for public Diuvita clinic profiles."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import as_int, parse_timestamp
from submit_discovery_candidates import load_env_file, run_psql


PUBLIC_STATUSES = ("published", "preliminary")


def load_coverage(limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    sql = f"""
with clinic_rows as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.status,
    case
      when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
        then jsonb_array_length(c.current_data -> 'profesionales')
      else 0
    end as specialist_entries,
    coalesce(claims.claim_count, 0) as specialist_claims,
    coalesce(reviews.open_review_count, 0) as open_review_count
  from public.clinics c
  left join lateral (
    select count(*) as claim_count
    from public.field_claims fc
    where fc.clinic_id = c.id
      and fc.field_path in ('professionals.published', 'team.public_professionals')
  ) claims on true
  left join lateral (
    select count(*) as open_review_count
    from public.review_queue rq
    where rq.clinic_id = c.id
      and rq.status = 'open'
      and (
        rq.payload ->> 'quality_context' = 'blocking_claims'
        or rq.payload::text ilike '%missing_professionals%'
        or rq.payload::text ilike '%profesionales%'
        or rq.payload::text ilike '%professionals%'
      )
  ) reviews on true
  where c.status in ('published', 'preliminary')
),
summary as (
  select jsonb_build_object(
    'visible_clinics', count(*),
    'with_specialists', count(*) filter (where specialist_entries > 0),
    'without_specialists', count(*) filter (where specialist_entries = 0),
    'total_specialist_entries', coalesce(sum(specialist_entries), 0),
    'clinics_with_specialist_claims', count(*) filter (where specialist_claims > 0),
    'clinics_with_open_specialist_reviews', count(*) filter (where open_review_count > 0)
  ) as data
  from clinic_rows
),
missing as (
  select coalesce(
    jsonb_agg(
      to_jsonb(items)
      order by items.open_review_count desc, items.specialist_claims desc, items.status, items.clinic_name
    ),
    '[]'::jsonb
  ) as data
  from (
    select slug, clinic_name, city, status, specialist_claims, open_review_count
    from clinic_rows
    where specialist_entries = 0
    order by open_review_count desc, specialist_claims desc, status, clinic_name
    limit {max(1, min(100, int(limit)))}
  ) items
),
covered as (
  select coalesce(jsonb_agg(to_jsonb(items) order by items.specialist_entries desc, items.clinic_name), '[]'::jsonb) as data
  from (
    select slug, clinic_name, city, status, specialist_entries, specialist_claims, open_review_count
    from clinic_rows
    where specialist_entries > 0
    order by specialist_entries desc, clinic_name
    limit {max(1, min(100, int(limit)))}
  ) items
)
select jsonb_build_object(
  'summary', (select data from summary),
  'missing_specialists', (select data from missing),
  'covered_specialists', (select data from covered),
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


def format_clinic_line(row: dict[str, Any], include_entries: bool = False) -> str:
    name = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    claims = as_int(row.get("specialist_claims"))
    reviews = as_int(row.get("open_review_count"))
    parts = [f"{name} · {city}", status]
    if include_entries:
        entries = as_int(row.get("specialist_entries"))
        parts.append(f"{entries} {plural(entries, 'especialista', 'especialistas')}")
    if claims:
        parts.append(f"{claims} {plural(claims, 'claim', 'claims')}")
    if reviews:
        parts.append(f"{reviews} {plural(reviews, 'revisión abierta', 'revisiones abiertas')}")
    return "- " + " · ".join(parts)


def prioritized_missing_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in report.get("missing_specialists") or [] if isinstance(row, dict)]
    return sorted(
        rows,
        key=lambda row: (
            -as_int(row.get("open_review_count")),
            -as_int(row.get("specialist_claims")),
            str(row.get("status") or ""),
            str(row.get("clinic_name") or row.get("slug") or ""),
        ),
    )


def next_specialist_action(report: dict[str, Any]) -> str:
    missing_rows = prioritized_missing_rows(report)
    if not missing_rows:
        return "No hay fichas visibles pendientes de especialistas."
    row = missing_rows[0]
    name = row.get("clinic_name") or row.get("slug") or "la primera ficha pendiente"
    reviews = as_int(row.get("open_review_count"))
    claims = as_int(row.get("specialist_claims"))
    if reviews:
        return f"Revisar {name}: ya tiene {reviews} {plural(reviews, 'revisión abierta', 'revisiones abiertas')}."
    if claims:
        return f"Revisar {name}: ya tiene {claims} {plural(claims, 'claim interno', 'claims internos')}."
    return f"Buscar especialistas publicados para {name} solo en fuentes oficiales."


def format_coverage(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    visible = as_int(summary.get("visible_clinics"))
    with_specialists = as_int(summary.get("with_specialists"))
    missing = as_int(summary.get("without_specialists"))
    lines = [
        "# Diuvita specialist coverage",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        "",
        "## Resumen",
        f"- Clínicas visibles: {visible}",
        f"- Con especialistas publicados: {with_specialists} ({pct(with_specialists, visible)})",
        f"- Sin especialistas publicados: {missing} ({pct(missing, visible)})",
        f"- Entradas de especialistas publicadas: {as_int(summary.get('total_specialist_entries'))}",
        f"- Clínicas con claims internos de especialistas: {as_int(summary.get('clinics_with_specialist_claims'))}",
        f"- Clínicas con revisión abierta sobre especialistas: {as_int(summary.get('clinics_with_open_specialist_reviews'))}",
        f"- Siguiente acción: {next_specialist_action(report)}",
        "- Writes data: no",
        "",
        "## Sin especialistas publicados",
    ]
    missing_rows = prioritized_missing_rows(report)
    if not missing_rows:
        lines.append("- Todas las clínicas visibles tienen especialistas publicados.")
    for row in missing_rows:
        lines.append(format_clinic_line(row))

    lines.extend(["", "## Con más especialistas publicados"])
    covered_rows = report.get("covered_specialists") or []
    if not covered_rows:
        lines.append("- No hay especialistas publicados todavía.")
    for row in covered_rows:
        lines.append(format_clinic_line(row, include_entries=True))

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_coverage(args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_coverage(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
