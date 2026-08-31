#!/usr/bin/env python3
"""Read-only brief for review-inbox bottlenecks."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from typing import Any

from admin_digest import SAFE_WRITE_REVIEW_BACKLOG_LIMIT, as_int, parse_timestamp, plural
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


def safe_limit(value: int) -> int:
    return max(1, min(50, int(value)))


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def load_backlog(limit: int, local_env: dict[str, str], clinic_query: str = "") -> dict[str, Any]:
    capped_limit = safe_limit(limit)
    clean_query = clinic_query.strip()
    query_literal = sql_literal(clean_query)
    like_literal = sql_literal(f"%{clean_query}%")
    compact_literal = sql_literal(f"%{compact_lookup_key(clean_query)}%")
    clinic_filter = "true"
    if clean_query:
        clinic_filter = f"""
    (
      rq.title ilike {like_literal}
      or c.slug ilike {like_literal}
      or c.display_name ilike {like_literal}
      or regexp_replace(translate(lower(coalesce(c.slug, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact_literal}
      or regexp_replace(translate(lower(coalesce(c.display_name, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact_literal}
    )
"""
    sql = f"""
with open_reviews as (
  select
    rq.id,
    rq.review_type,
    rq.priority,
    rq.title,
    rq.payload,
    rq.created_at,
    rq.updated_at,
    rq.clinic_id,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city,
    c.status as clinic_status
  from public.review_queue rq
  left join public.clinics c on c.id = rq.clinic_id
  where rq.status = 'open'
    and {clinic_filter}
),
review_type_summary as (
  select coalesce(jsonb_agg(to_jsonb(grouped) order by grouped.open_count desc, grouped.review_type), '[]'::jsonb) as data
  from (
    select
      review_type,
      count(*) as open_count,
      min(created_at) as oldest_created_at,
      max(priority) as max_priority
    from (
      select
        case
          when review_type = 'clinic_quality_audit'
            and payload ->> 'quality_context' = 'blocking_claims'
            then 'claims bloqueantes'
          when review_type = 'clinic_quality_audit' then 'auditorias de calidad'
          when review_type = 'clinic_profile_enrichment' then 'mejoras de ficha'
          when review_type = 'candidate_clinic' then 'clinicas candidatas'
          when review_type = 'source_change_detected' then 'cambios de fuente'
          else review_type
        end as review_type,
        priority,
        created_at
      from open_reviews
    ) typed
    group by review_type
  ) grouped
),
duplicate_enrichment_groups as (
  select
    clinic_id,
    coalesce(clinic_name, clinic_slug, 'sin clínica') as clinic_name,
    clinic_slug,
    city,
    clinic_status,
    count(*) as card_count,
    max(priority) as max_priority,
    min(created_at) as oldest_created_at,
    jsonb_agg(
      jsonb_build_object(
        'id', id,
        'title', title,
        'priority', priority,
        'created_at', created_at,
        'updated_at', updated_at
      )
      order by priority desc, created_at asc
    ) as cards
  from open_reviews
  where review_type = 'clinic_profile_enrichment'
    and clinic_id is not null
  group by clinic_id, clinic_name, clinic_slug, city, clinic_status
  having count(*) > 1
),
duplicate_enrichment as (
  select coalesce(
    jsonb_agg(
      to_jsonb(items)
      order by items.card_count desc, items.max_priority desc, items.oldest_created_at asc
    ),
    '[]'::jsonb
  ) as data
  from (
    select *
    from duplicate_enrichment_groups
    order by card_count desc, max_priority desc, oldest_created_at asc
    limit {capped_limit}
  ) items
),
clinic_workgroups as (
  select coalesce(
    jsonb_agg(
      to_jsonb(items)
      order by
        items.blocking_claim_reviews desc,
        items.card_count desc,
        items.max_priority desc,
        items.oldest_created_at asc
    ),
    '[]'::jsonb
  ) as data
  from (
    select
      clinic_id,
      coalesce(clinic_name, clinic_slug, 'sin clínica') as clinic_name,
      clinic_slug,
      city,
      clinic_status,
      count(*) as card_count,
      count(*) filter (
        where review_type = 'clinic_quality_audit'
          and payload ->> 'quality_context' = 'blocking_claims'
      ) as blocking_claim_reviews,
      count(*) filter (
        where review_type = 'clinic_quality_audit'
          and coalesce(payload ->> 'quality_context', '') <> 'blocking_claims'
      ) as quality_reviews,
      count(*) filter (where review_type = 'clinic_profile_enrichment') as enrichment_reviews,
      count(*) filter (where review_type = 'source_change_detected') as source_change_reviews,
      count(*) filter (where review_type = 'candidate_clinic') as candidate_reviews,
      max(priority) as max_priority,
      min(created_at) as oldest_created_at,
      jsonb_agg(
        jsonb_build_object(
          'id', id,
          'review_type', review_type,
          'title', title,
          'priority', priority,
          'created_at', created_at,
          'updated_at', updated_at
        )
        order by
          case
            when review_type = 'clinic_quality_audit'
              and payload ->> 'quality_context' = 'blocking_claims' then 1
            when review_type = 'source_change_detected' then 2
            when review_type = 'clinic_profile_enrichment' then 3
            when review_type = 'clinic_quality_audit' then 4
            when review_type = 'candidate_clinic' then 5
            else 9
          end,
          priority desc,
          created_at asc
      ) as cards
    from open_reviews
    where clinic_id is not null
    group by clinic_id, clinic_name, clinic_slug, city, clinic_status
    order by
      blocking_claim_reviews desc,
      card_count desc,
      max_priority desc,
      oldest_created_at asc
    limit {capped_limit}
  ) items
),
summary as (
  select jsonb_build_object(
    'open_reviews', (select count(*) from open_reviews),
    'open_enrichment_reviews', count(*) filter (where review_type = 'clinic_profile_enrichment'),
    'duplicate_enrichment_clinics', (select count(*) from duplicate_enrichment_groups),
    'duplicate_enrichment_reviews', coalesce((select sum(card_count) from duplicate_enrichment_groups), 0),
    'safe_write_limit', {SAFE_WRITE_REVIEW_BACKLOG_LIMIT}
  ) as data
  from open_reviews
)
select jsonb_build_object(
  'clinic_query', {query_literal},
  'summary', (select data from summary),
  'review_type_summary', (select data from review_type_summary),
  'clinic_workgroups', (select data from clinic_workgroups),
  'duplicate_enrichment', (select data from duplicate_enrichment),
  'generated_at', now()
);
"""
    return json.loads(run_psql(sql, local_env))


def backlog_guard(summary: dict[str, Any]) -> str:
    open_reviews = as_int(summary.get("open_reviews"))
    limit = as_int(summary.get("safe_write_limit")) or SAFE_WRITE_REVIEW_BACKLOG_LIMIT
    if open_reviews >= limit:
        return f"freno activo: {open_reviews}/{limit} revisiones abiertas"
    if limit - open_reviews <= 5:
        return f"cerca del freno: {open_reviews}/{limit} abiertas"
    return f"normal: {open_reviews}/{limit} abiertas"


def status_label(status: Any) -> str:
    labels = {
        "published": "publicada",
        "preliminary": "preliminar",
        "draft": "borrador",
        "review": "en revisión",
    }
    return labels.get(str(status or ""), str(status or "sin estado"))


def review_type_label(review_type: Any) -> str:
    labels = {
        "clinic_quality_audit": "auditoría",
        "clinic_profile_enrichment": "mejora",
        "candidate_clinic": "clínica candidata",
        "source_change_detected": "cambio de fuente",
    }
    return labels.get(str(review_type or ""), str(review_type or "revisión"))


def format_duplicate_group(row: dict[str, Any]) -> str:
    name = row.get("clinic_name") or row.get("clinic_slug") or "sin clínica"
    city = row.get("city") or "sin ciudad"
    status = status_label(row.get("clinic_status"))
    cards = as_int(row.get("card_count"))
    priority = as_int(row.get("max_priority"))
    oldest = parse_timestamp(row.get("oldest_created_at"))
    return (
        f"- {name} · {city} · {status} · "
        f"{cards} {plural(cards, 'tarjeta', 'tarjetas')} · P{priority} · más antigua {oldest}"
    )


def workgroup_order(row: dict[str, Any]) -> str:
    steps = []
    if as_int(row.get("blocking_claim_reviews")):
        steps.append("claims bloqueantes")
    if as_int(row.get("source_change_reviews")):
        steps.append("fuentes cambiadas")
    if as_int(row.get("enrichment_reviews")):
        steps.append("mejoras")
    if as_int(row.get("quality_reviews")):
        steps.append("auditorías")
    if as_int(row.get("candidate_reviews")):
        steps.append("candidatas")
    return " -> ".join(steps) if steps else "prioridad normal"


def workgroup_recommendation(row: dict[str, Any]) -> str:
    if as_int(row.get("blocking_claim_reviews")):
        return "primero quitar o corregir datos dudosos"
    if as_int(row.get("source_change_reviews")):
        return "primero revisar qué cambió en la fuente"
    if as_int(row.get("enrichment_reviews")):
        return "consolidar una sola versión de ficha"
    return "revisar juntas antes de cerrar"


def format_clinic_workgroup(row: dict[str, Any]) -> str:
    name = row.get("clinic_name") or row.get("clinic_slug") or "sin clínica"
    city = row.get("city") or "sin ciudad"
    status = status_label(row.get("clinic_status"))
    cards = as_int(row.get("card_count"))
    priority = as_int(row.get("max_priority"))
    oldest = parse_timestamp(row.get("oldest_created_at"))
    parts = []
    for key, singular, plural_text in [
        ("blocking_claim_reviews", "claim bloqueante", "claims bloqueantes"),
        ("enrichment_reviews", "mejora", "mejoras"),
        ("source_change_reviews", "cambio de fuente", "cambios de fuente"),
        ("quality_reviews", "auditoría", "auditorías"),
        ("candidate_reviews", "candidata", "candidatas"),
    ]:
        count = as_int(row.get(key))
        if count:
            parts.append(f"{count} {plural(count, singular, plural_text)}")
    detail = " / ".join(parts) if parts else "sin tipo medido"
    return (
        f"- {name} · {city} · {status} · "
        f"{cards} {plural(cards, 'tarjeta', 'tarjetas')} · {detail} · "
        f"P{priority} · más antigua {oldest} · "
        f"orden: {workgroup_order(row)} · {workgroup_recommendation(row)}"
    )


def format_workgroup_card(card: dict[str, Any]) -> str:
    title = card.get("title") or "Revisión abierta"
    review_type = review_type_label(card.get("review_type"))
    priority = as_int(card.get("priority"))
    created = parse_timestamp(card.get("created_at"))
    return f"  - {title}: {review_type} · P{priority} · creada {created}"


def first_backlog_action(report: dict[str, Any]) -> str:
    workgroups = report.get("clinic_workgroups") or []
    blocking_workgroups = [
        row for row in workgroups if as_int(row.get("blocking_claim_reviews"))
    ]
    if blocking_workgroups:
        first = blocking_workgroups[0]
        name = first.get("clinic_name") or first.get("clinic_slug") or "la primera clínica bloqueada"
        cards = as_int(first.get("card_count"))
        return (
            f"Revisar {name}: {cards} {plural(cards, 'tarjeta', 'tarjetas')}, "
            f"empezando por claims bloqueantes"
        )
    duplicates = report.get("duplicate_enrichment") or []
    if duplicates:
        first = duplicates[0]
        name = first.get("clinic_name") or first.get("clinic_slug") or "la primera clínica duplicada"
        cards = as_int(first.get("card_count"))
        return f"Revisar {name}: tiene {cards} {plural(cards, 'mejora abierta', 'mejoras abiertas')}"
    summary = report.get("summary") or {}
    open_reviews = as_int(summary.get("open_reviews"))
    if open_reviews:
        return "No hay mejoras duplicadas; seguir por la prioridad normal del panel"
    return "No hay revisiones abiertas"


def format_backlog(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    duplicates = report.get("duplicate_enrichment") or []
    workgroups = report.get("clinic_workgroups") or []
    clinic_query = str(report.get("clinic_query") or "").strip()
    output = [
        "# Vitalarga: atascos de bandeja",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
    ]
    if clinic_query:
        output.append(f"Consulta: {clinic_query}")
    output.extend([
        "",
        "## Resumen",
        f"- Revisiones abiertas: {as_int(summary.get('open_reviews'))}",
        f"- Mejoras de ficha abiertas: {as_int(summary.get('open_enrichment_reviews'))}",
        f"- Clínicas con varias mejoras abiertas: {as_int(summary.get('duplicate_enrichment_clinics'))}",
        f"- Tarjetas en grupos duplicados: {as_int(summary.get('duplicate_enrichment_reviews'))}",
        f"- Freno de bandeja: {backlog_guard(summary)}",
        "- Writes data: no",
        "",
        "## Empezar por",
        f"- {first_backlog_action(report)}",
        "",
        "## Trabajar por clínica",
    ])
    if not workgroups:
        output.append("- No hay grupos de revisión por clínica.")
    for row in workgroups:
        output.append(format_clinic_workgroup(row))
    if clinic_query and workgroups:
        output.extend(["", "## Tarjetas del caso"])
        for row in workgroups:
            cards = [card for card in row.get("cards") or [] if isinstance(card, dict)]
            if not cards:
                continue
            output.append(f"- {row.get('clinic_name') or row.get('clinic_slug') or 'sin clínica'}")
            output.extend(format_workgroup_card(card) for card in cards)

    output.extend([
        "",
        "## Tipos abiertos",
    ])
    for row in report.get("review_type_summary") or []:
        count = as_int(row.get("open_count"))
        open_label = plural(count, "abierta", "abiertas")
        output.append(
            f"- {row.get('review_type') or 'revisión'}: {count} {open_label}; máxima prioridad P{as_int(row.get('max_priority'))}"
        )

    output.extend(["", "## Varias mejoras abiertas para la misma clínica"])
    if not duplicates:
        output.append("- No hay grupos duplicados de mejoras de ficha.")
    for row in duplicates:
        output.append(format_duplicate_group(row))

    output.extend([
        "",
        "Nota: esto no descarta ni resuelve tarjetas. Solo ayuda a decidir qué revisar primero en `/admin/`.",
    ])
    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--clinic", default="", help="Optional clinic name or slug to focus the backlog.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_backlog(args.limit, load_env_file(), args.clinic)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_backlog(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
