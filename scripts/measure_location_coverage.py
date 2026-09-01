#!/usr/bin/env python3
"""Read-only location coverage report for visible Vitalarga clinic profiles."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import SAFE_WRITE_REVIEW_BACKLOG_LIMIT, as_int, parse_timestamp, plural
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
	location_review_proposals as (
	  select
	    c.id,
	    c.slug,
	    c.clinic_name,
	    c.clinic_city,
	    c.status,
	    count(*) as open_review_count,
	    coalesce(sum(jsonb_array_length(proposed.locations)), 0) as proposed_location_count
	  from visible_clinics c
	  join public.review_queue rq on rq.clinic_id = c.id
	  cross join lateral (
	    select case
	      when jsonb_typeof(coalesce(
	        rq.payload #> '{{proposed_fields,locations}}',
	        rq.payload #> '{{proposed_current_data,locations}}',
	        rq.payload #> '{{fields,locations}}'
	      )) = 'array'
	        then coalesce(
	          rq.payload #> '{{proposed_fields,locations}}',
	          rq.payload #> '{{proposed_current_data,locations}}',
	          rq.payload #> '{{fields,locations}}'
	        )
	      else '[]'::jsonb
	    end as locations
	  ) proposed
	  where rq.status = 'open'
	    and rq.review_type = 'clinic_profile_enrichment'
	    and jsonb_array_length(proposed.locations) > 0
	  group by c.id, c.slug, c.clinic_name, c.clinic_city, c.status
	),
	location_claims as (
	  select
	    c.id,
	    c.slug,
	    c.clinic_name,
	    c.clinic_city,
	    c.status,
	    count(*) as claim_count,
	    coalesce(sum(
	      case
	        when jsonb_typeof(fc.value) = 'array' then jsonb_array_length(fc.value)
	        when fc.value is not null then 1
	        else 0
	      end
	    ), 0) as location_claim_count
	  from visible_clinics c
	  join public.field_claims fc on fc.clinic_id = c.id
	    where fc.field_path = 'location.locations'
	    and fc.verification_status not in ('rejected', 'stale')
	  group by c.id, c.slug, c.clinic_name, c.clinic_city, c.status
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
    {location_maps_check} as has_google_maps_profile
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
      case when not has_google_maps_profile then 'Google Maps de clínica' end
    ], null) as pending_fields
  from location_rows lr
),
	summary as (
	  select jsonb_build_object(
	    'visible_clinics', (select count(*) from visible_clinics),
	    'open_reviews', (select count(*) from public.review_queue where status = 'open'),
	    'safe_write_limit', {SAFE_WRITE_REVIEW_BACKLOG_LIMIT},
	    'clinics_with_locations', count(distinct id),
	    'multi_location_clinics', count(distinct id) filter (where clinic_location_count > 1),
	    'total_locations', count(*),
	    'locations_with_address', count(*) filter (where has_address),
	    'locations_missing_address', count(*) filter (where not has_address),
	    'locations_with_google_maps_profile', count(*) filter (where has_google_maps_profile),
	    'locations_missing_google_maps_profile', count(*) filter (where not has_google_maps_profile),
	    'clinics_with_location_proposals', (select count(*) from location_review_proposals),
	    'proposed_location_rows', coalesce((select sum(proposed_location_count) from location_review_proposals), 0),
	    'clinics_with_location_claims', (select count(*) from location_claims),
	    'internal_location_rows', coalesce((select sum(location_claim_count) from location_claims), 0)
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
	),
	pending_location_proposals as (
	  select coalesce(
	    jsonb_agg(
	      to_jsonb(items)
	      order by items.open_review_count desc,
	        items.proposed_location_count desc,
	        case when items.status = 'published' then 0 else 1 end,
	        items.clinic_name
	    ),
	    '[]'::jsonb
	  ) as data
	  from (
	    select
	      slug,
	      clinic_name,
	      clinic_city,
	      status,
	      open_review_count,
	      proposed_location_count
	    from location_review_proposals
	    order by open_review_count desc,
	      proposed_location_count desc,
	      case when status = 'published' then 0 else 1 end,
	      clinic_name
	    limit {capped_limit}
	  ) items
	),
	pending_location_claims as (
	  select coalesce(
	    jsonb_agg(
	      to_jsonb(items)
	      order by items.location_claim_count desc,
	        items.claim_count desc,
	        case when items.status = 'published' then 0 else 1 end,
	        items.clinic_name
	    ),
	    '[]'::jsonb
	  ) as data
	  from (
	    select
	      slug,
	      clinic_name,
	      clinic_city,
	      status,
	      claim_count,
	      location_claim_count
	    from location_claims
	    order by location_claim_count desc,
	      claim_count desc,
	      case when status = 'published' then 0 else 1 end,
	      clinic_name
	    limit {capped_limit}
	  ) items
	)
	select jsonb_build_object(
	  'summary', (select data from summary),
	  'pending_locations', (select data from pending_locations),
	  'next_location_target', (select data from next_location_target),
	  'pending_location_proposals', (select data from pending_location_proposals),
	  'pending_location_claims', (select data from pending_location_claims),
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


def location_next_step(row: dict[str, Any]) -> str:
    clinic = str(row.get("clinic_name") or row.get("slug") or "esta clínica")
    location = location_name(row)
    pending = [str(item).strip() for item in row.get("pending_fields") or [] if str(item).strip()]
    if "Dirección" in pending:
        return f"completar la dirección exacta de {location} en {clinic}"
    if "Google Maps de clínica" in pending:
        return (
            f"añadir el perfil real de Google Business de {clinic} para {location}; "
            "no usar búsqueda, ruta ni enlace de dirección"
        )
    if pending:
        return f"revisar {location} de {clinic}: pendiente {', '.join(pending)}"
    return f"revisar {location} de {clinic}"


def location_review_backlog_guard(summary: dict[str, Any]) -> str:
    open_reviews = as_int(summary.get("open_reviews"))
    limit = as_int(summary.get("safe_write_limit")) or SAFE_WRITE_REVIEW_BACKLOG_LIMIT
    if "open_reviews" not in summary:
        return "sin dato de bandeja"
    if open_reviews >= limit:
        return f"freno activo: {open_reviews}/{limit} revisiones abiertas"
    if limit - open_reviews <= 5:
        return f"cerca del freno: {open_reviews}/{limit} revisiones abiertas"
    return f"con margen: {open_reviews}/{limit} revisiones abiertas"


def should_defer_location_review_creation(summary: dict[str, Any]) -> bool:
    if "open_reviews" not in summary:
        return False
    limit = as_int(summary.get("safe_write_limit")) or SAFE_WRITE_REVIEW_BACKLOG_LIMIT
    return as_int(summary.get("open_reviews")) >= limit - 5


def next_location_action(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    target = report.get("next_location_target") or {}
    if isinstance(target, dict) and target:
        clinic = str(target.get("clinic_name") or target.get("slug") or "la primera clínica")
        location = location_name(target)
        pending = [str(item) for item in target.get("pending_fields") or [] if str(item).strip()]
        if pending:
            return f"Revisar {location} de {clinic}: {location_next_step(target)}"
        return f"Revisar sedes de {clinic}"
    proposal = first_location_proposal(report)
    if proposal:
        clinic = str(proposal.get("clinic_name") or proposal.get("slug") or "la primera clínica")
        count = as_int(proposal.get("proposed_location_count"))
        return f"Revisar sedes propuestas de {clinic}: {count} {plural(count, 'sede detectada', 'sedes detectadas')} en bandeja"
    claim = first_location_claim(report)
    if claim:
        clinic = str(claim.get("clinic_name") or claim.get("slug") or "la primera clínica")
        count = as_int(claim.get("location_claim_count"))
        if should_defer_location_review_creation(summary):
            return (
                f"Bajar bandeja antes de crear propuestas de sedes: {clinic} tiene "
                f"{count} {plural(count, 'sede detectada interna', 'sedes detectadas internas')}"
            )
        return f"Preparar revisión de sedes para {clinic}: {count} {plural(count, 'sede detectada interna', 'sedes detectadas internas')}"
    return "sin sedes pendientes medidas"


def format_location_row(row: dict[str, Any]) -> str:
    clinic = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("clinic_city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    location = location_name(row)
    location_count = as_int(row.get("clinic_location_count"))
    pending = ", ".join(str(item) for item in row.get("pending_fields") or [])
    location_note = f"{location_count} {plural(location_count, 'sede', 'sedes')}" if location_count else "sede"
    return (
        f"- {clinic} · {city} · {status} · {location} · {location_note} · "
        f"pendiente: {pending} · siguiente: {location_next_step(row)}"
    )


def first_location_proposal(report: dict[str, Any]) -> dict[str, Any] | None:
    rows = [row for row in report.get("pending_location_proposals") or [] if isinstance(row, dict)]
    return rows[0] if rows else None


def first_location_claim(report: dict[str, Any]) -> dict[str, Any] | None:
    rows = [row for row in report.get("pending_location_claims") or [] if isinstance(row, dict)]
    return rows[0] if rows else None


def format_location_proposal_row(row: dict[str, Any]) -> str:
    clinic = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("clinic_city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    proposed = as_int(row.get("proposed_location_count"))
    reviews = as_int(row.get("open_review_count"))
    return (
        f"- {clinic} · {city} · {status} · "
        f"{proposed} {plural(proposed, 'sede detectada', 'sedes detectadas')} · "
        f"{reviews} {plural(reviews, 'revisión abierta', 'revisiones abiertas')} · "
        "siguiente: cargar sedes detectadas en el editor y guardar solo tras revisión humana"
    )


def format_location_claim_row(row: dict[str, Any], summary: dict[str, Any] | None = None) -> str:
    clinic = row.get("clinic_name") or row.get("slug") or "sin nombre"
    city = row.get("clinic_city") or "sin ciudad"
    status = status_label(str(row.get("status") or ""))
    detected = as_int(row.get("location_claim_count"))
    claims = as_int(row.get("claim_count"))
    if summary and should_defer_location_review_creation(summary):
        next_step = "siguiente: esperar; primero bajar la bandeja de revisión"
    else:
        next_step = "siguiente: convertir en propuesta revisable cuando haya espacio en la bandeja"
    return (
        f"- {clinic} · {city} · {status} · "
        f"{detected} {plural(detected, 'sede detectada interna', 'sedes detectadas internas')} · "
        f"{claims} {plural(claims, 'evidencia', 'evidencias')} · "
        f"{next_step}"
    )


def format_location_coverage(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    total_locations = as_int(summary.get("total_locations"))
    maps_ready = as_int(summary.get("locations_with_google_maps_profile"))
    address_ready = as_int(summary.get("locations_with_address"))
    rows = report.get("pending_locations") or []
    proposal_rows = report.get("pending_location_proposals") or []
    claim_rows = report.get("pending_location_claims") or []
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
        f"- Bandeja de revisión: {location_review_backlog_guard(summary)}",
        f"- Clínicas con sedes propuestas en bandeja: {as_int(summary.get('clinics_with_location_proposals'))}",
        f"- Sedes propuestas en bandeja: {as_int(summary.get('proposed_location_rows'))}",
        f"- Clínicas con sedes detectadas internas: {as_int(summary.get('clinics_with_location_claims'))}",
        f"- Sedes detectadas internas: {as_int(summary.get('internal_location_rows'))}",
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
    lines.extend(["", "## Sedes propuestas en bandeja"])
    if not proposal_rows:
        lines.append("- No hay sedes propuestas esperando revisión.")
    for row in proposal_rows:
        lines.append(format_location_proposal_row(row))
    lines.extend(["", "## Sedes detectadas internas"])
    if not claim_rows:
        lines.append("- No hay sedes detectadas en evidencias internas.")
    for row in claim_rows:
        lines.append(format_location_claim_row(row, summary))
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
