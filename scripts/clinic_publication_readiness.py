#!/usr/bin/env python3
"""Read-only publication readiness report for Vitalarga clinics."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from typing import Any

from admin_digest import as_int, parse_timestamp
from google_maps_url_rules import google_maps_profile_link_predicate
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


PUBLIC_STATUSES = {"published", "preliminary"}
STATUS_LABELS = {
    "published": "publicada",
    "preliminary": "preliminar",
    "draft": "borrador",
    "review": "revision interna",
    "verified": "verificada interna",
    "extracted": "extraida interna",
    "discovered": "descubierta interna",
    "archived": "archivada",
}
REQUIRED_FIELDS = (
    ("has_name", "Nombre"),
    ("has_city", "Ciudad"),
    ("has_country", "Pais"),
    ("has_website", "Web oficial"),
    ("has_address", "Direccion o sede"),
    ("has_summary", "Resumen suficiente"),
    ("has_services", "Servicios principales"),
    ("has_google_maps", "Google Maps de clinica"),
)
FIX_HINTS = {
    "Nombre": "campo Nombre del editor de clinica.",
    "Ciudad": "campo Ciudad del editor de clinica.",
    "Pais": "campo Pais del editor de clinica.",
    "Web oficial": "campo Web; debe ser la web oficial de la clinica.",
    "Direccion o sede": "bloque Sedes y acceso; anade direccion o sede completa.",
    "Resumen suficiente": "campo Resumen; redacta una descripcion neutra con informacion publica.",
    "Servicios principales": "campo Servicios; anade servicios publicados por la clinica.",
    "Google Maps de clinica": "campo Google Maps; pega el perfil real de la clinica, no una busqueda ni una direccion.",
    "Claims bloqueantes": "bandeja de revision; corrige, deja fuera o descarta los datos dudosos antes de publicar.",
}


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def load_readiness(query: str, limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    clean_query = query.strip()
    capped_limit = max(1, min(100, int(limit)))
    sql_limit = capped_limit if clean_query else 100
    has_google_maps = google_maps_profile_link_predicate("maps_url", "google_maps_url", "map_url")
    query_literal = sql_literal(clean_query)
    like_literal = sql_literal(f"%{clean_query}%")
    compact_literal = sql_literal(f"%{compact_lookup_key(clean_query)}%")
    clinic_filter = "coalesce(c.status, '') <> 'archived'"
    if clean_query:
        clinic_filter = f"""
  (
    lower(c.slug) = lower({query_literal})
    or c.slug ilike {like_literal}
    or c.display_name ilike {like_literal}
    or regexp_replace(translate(lower(coalesce(c.slug, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact_literal}
    or regexp_replace(translate(lower(coalesce(c.display_name, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact_literal}
  )
"""
    sql = f"""
with clinic_rows as (
  select
    c.id,
    c.slug,
    c.display_name as clinic_name,
    c.city,
    c.country,
    c.status,
    c.updated_at,
    nullif(btrim(coalesce(c.display_name, c.current_data ->> 'name', '')), '') is not null as has_name,
    nullif(btrim(coalesce(c.city, c.current_data ->> 'city', '')), '') is not null as has_city,
    nullif(btrim(coalesce(c.country, c.current_data ->> 'country', '')), '') is not null as has_country,
    nullif(btrim(coalesce(c.website, c.current_data ->> 'web', '')), '') is not null as has_website,
    length(btrim(coalesce(c.summary, c.current_data ->> 'summary', ''))) >= 120 as has_summary,
    (
      nullif(btrim(coalesce(c.address, c.current_data ->> 'address', '')), '') is not null
      or exists (
        select 1
        from jsonb_array_elements(
          case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else '[]'::jsonb
          end
        ) as location(value)
        where nullif(btrim(coalesce(
          location.value ->> 'address',
          location.value ->> 'direccion',
          location.value ->> 'dirección',
          case
            when jsonb_typeof(location.value) = 'string'
              then location.value #>> '{{}}'
            else ''
          end
        )), '') is not null
      )
    ) as has_address,
    {has_google_maps} as has_google_maps,
    case
      when jsonb_typeof(c.current_data -> 'services') = 'array'
        then jsonb_array_length(c.current_data -> 'services') > 0
      else false
    end as has_services,
    coalesce(reviews.open_reviews, 0) as open_reviews,
    coalesce(reviews.open_blocking_reviews, 0) as open_blocking_reviews
  from public.clinics c
  left join lateral (
    select
      count(*) as open_reviews,
      count(*) filter (
        where rq.review_type = 'clinic_quality_audit'
          and rq.payload ->> 'quality_context' = 'blocking_claims'
      ) as open_blocking_reviews
    from public.review_queue rq
    where rq.clinic_id = c.id
      and rq.status = 'open'
  ) reviews on true
  where {clinic_filter}
  order by
    case when lower(c.slug) = lower({query_literal}) then 0 else 1 end,
    case when c.status in ('published', 'preliminary') then 0 else 1 end,
    c.display_name
  limit {sql_limit}
)
select jsonb_build_object(
  'query', {query_literal},
  'matches', coalesce(jsonb_agg(to_jsonb(clinic_rows)), '[]'::jsonb),
  'generated_at', now(),
  'writes_data', false
)
from clinic_rows;
"""
    report = json.loads(run_psql(sql, local_env))
    matches = sort_matches(report.get("matches") or [], focused=bool(clean_query))
    report["summary"] = readiness_summary(matches)
    report["matches"] = matches if clean_query else matches[:capped_limit]
    return report


def status_label(status: Any) -> str:
    return STATUS_LABELS.get(str(status or ""), str(status or "-"))


def missing_required_fields(row: dict[str, Any]) -> list[str]:
    missing = [label for key, label in REQUIRED_FIELDS if not row.get(key)]
    if as_int(row.get("open_blocking_reviews")):
        missing.append("Claims bloqueantes")
    return missing


def sort_matches(matches: list[dict[str, Any]], focused: bool = False) -> list[dict[str, Any]]:
    if focused:
        return matches
    return sorted(
        matches,
        key=lambda row: (
            -len(missing_required_fields(row)),
            -as_int(row.get("open_blocking_reviews")),
            0 if str(row.get("status") or "") not in PUBLIC_STATUSES else 1,
            str(row.get("clinic_name") or row.get("slug") or ""),
        ),
    )


def readiness_summary(matches: list[dict[str, Any]]) -> dict[str, Any]:
    missing_counts: dict[str, int] = {}
    ready = 0
    blocking = 0
    visible = 0
    for row in matches:
        missing = missing_required_fields(row)
        if not missing:
            ready += 1
        for label in missing:
            missing_counts[label] = missing_counts.get(label, 0) + 1
        if as_int(row.get("open_blocking_reviews")):
            blocking += 1
        if str(row.get("status") or "") in PUBLIC_STATUSES:
            visible += 1
    top_missing = sorted(missing_counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        "clinics_measured": len(matches),
        "visible_clinics": visible,
        "ready_clinics": ready,
        "clinics_with_missing_fields": len(matches) - ready,
        "clinics_with_blocking_reviews": blocking,
        "top_missing_fields": [
            {"field": label, "count": count}
            for label, count in top_missing[:5]
        ],
    }


def visibility_message(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "")
    label = status_label(status)
    if status in PUBLIC_STATUSES:
        return f"Visible en la web como {label}, tras la ultima publicacion estatica."
    return f"No visible: esta como {label}. Para aparecer debe pasar a preliminar o publicada."


def next_publication_step(row: dict[str, Any], missing: list[str]) -> str:
    status = str(row.get("status") or "")
    if missing:
        first = missing[0]
        if status in PUBLIC_STATUSES:
            return f"Completar primero: {first}. La ficha ya es visible, pero no esta lista sin ese punto."
        return f"Completar primero: {first}. Despues podra pasar a preliminar o publicada si Daniel lo valida."
    if status in PUBLIC_STATUSES:
        return "No hay faltantes obligatorios; si no ves cambios online, revisa si falta regenerar la web publica."
    return "No hay faltantes obligatorios; Daniel puede decidir si pasa a preliminar o publicada."


def missing_fix_hints(missing: list[str]) -> list[tuple[str, str]]:
    return [(label, FIX_HINTS.get(label, "abre la ficha y revisa este punto.")) for label in missing]


def format_match(row: dict[str, Any]) -> list[str]:
    missing = missing_required_fields(row)
    name = row.get("clinic_name") or row.get("slug") or "Clinica sin nombre"
    slug = row.get("slug") or "-"
    city = row.get("city") or "sin ciudad"
    lines = [
        f"## {name}",
        f"- Slug: {slug}",
        f"- Ciudad: {city}",
        f"- Estado: {status_label(row.get('status'))}",
        f"- Visibilidad: {visibility_message(row)}",
        f"- Ultima edicion: {parse_timestamp(row.get('updated_at'))}",
        f"- Revisiones abiertas: {as_int(row.get('open_reviews'))}",
    ]
    if missing:
        lines.append("- Falta para publicar: " + ", ".join(missing))
        lines.append("- Donde corregirlo:")
        for label, hint in missing_fix_hints(missing):
            lines.append(f"  - {label}: {hint}")
    else:
        lines.append("- Falta para publicar: nada obligatorio detectado")
    lines.append(f"- Siguiente paso: {next_publication_step(row, missing)}")
    return lines


def format_readiness(report: dict[str, Any]) -> str:
    query = report.get("query") or "-"
    matches = report.get("matches") or []
    summary = report.get("summary") or readiness_summary(matches)
    top_missing = summary.get("top_missing_fields") or []
    top_missing_label = ", ".join(
        f"{item.get('field')}: {as_int(item.get('count'))}"
        for item in top_missing
        if isinstance(item, dict)
    ) or "sin faltantes"
    lines = [
        "# Vitalarga publication readiness",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        f"Consulta: {query if query != '-' else 'todas las fichas no archivadas'}",
        "- Writes data: no",
        "",
        "## Resumen",
        f"- Clínicas medidas: {as_int(summary.get('clinics_measured') or len(matches))}",
        f"- Mostradas: {len(matches)}",
        f"- Visibles: {as_int(summary.get('visible_clinics'))}",
        f"- Sin faltantes obligatorios: {as_int(summary.get('ready_clinics'))}",
        f"- Con faltantes: {as_int(summary.get('clinics_with_missing_fields'))}",
        f"- Con claims bloqueantes: {as_int(summary.get('clinics_with_blocking_reviews'))}",
        f"- Faltantes principales: {top_missing_label}",
        "",
    ]
    if not matches:
        lines.extend([
            "## Resultado",
            "- No he encontrado una clinica con ese nombre o slug.",
        ])
        return "\n".join(lines) + "\n"
    if len(matches) > 1:
        if query == "-":
            lines.append(f"Mostrando {len(matches)} fichas prioritarias por faltantes:")
        else:
            lines.append(f"Encontradas {len(matches)} coincidencias. Revisa la correcta:")
        lines.append("")
    for index, row in enumerate(matches):
        if index:
            lines.append("")
        lines.extend(format_match(row))
    lines.extend([
        "",
        "Nota: este informe no publica, no edita fichas y no cambia Netlify.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic", default="", help="Optional clinic slug or name fragment.")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = load_readiness(args.clinic, args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_readiness(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
