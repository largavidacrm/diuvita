#!/usr/bin/env python3
"""Read-only brief for review-inbox bottlenecks."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from typing import Any

from admin_digest import SAFE_WRITE_REVIEW_BACKLOG_LIMIT, as_int, parse_timestamp, plural
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


PHONE_RE = re.compile(r"(?:\+34|0034|34)?[\s().-]*[6789](?:[\s().-]*\d){8}")

FIELD_LABELS = {
    "display_name": "Nombre",
    "name": "Nombre",
    "web": "Web",
    "website": "Web",
    "country": "País",
    "city": "Ciudad",
    "region": "Región",
    "address": "Dirección",
    "locations": "Sedes",
    "maps_url": "Google Maps",
    "google_maps_url": "Google Maps",
    "google_reviews_url": "Valoraciones Google",
    "reviews_url": "Valoraciones Google",
    "summary": "Resumen",
    "services": "Servicios",
    "specialties": "Especialidades",
    "unidades": "Unidades",
    "profesionales": "Especialistas",
    "professionals": "Especialistas",
    "years_in_practice": "Años en ejercicio",
    "specialists_count": "Número de especialistas",
    "team_credentialing_visible": "Colegiación visible",
    "public_pricing": "Precio público",
    "pricing_url": "Página de precios",
    "tech": "Tecnología",
    "email": "Email",
    "telefono": "Teléfono principal",
    "phone": "Teléfono principal",
    "telephone": "Teléfono principal",
    "phone_fixed": "Teléfono fijo",
    "phone_mobile": "Móvil",
    "phone_whatsapp": "WhatsApp",
    "instagram": "Instagram",
}

PHONE_FIELD_KEYS = {"telefono", "phone", "telephone", "phone_fixed", "phone_mobile", "phone_whatsapp"}


def safe_limit(value: int) -> int:
    return max(1, min(50, int(value)))


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def has_visible_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_visible_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_visible_value(item) for item in value.values())
    return True


def proposed_fields(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("proposed_fields", "proposed_current_data", "fields"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def field_label(key: str) -> str:
    return FIELD_LABELS.get(str(key), str(key).replace("_", " "))


def proposal_field_labels(payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for key, value in proposed_fields(payload).items():
        if not has_visible_value(value):
            continue
        label = field_label(str(key))
        if label not in seen:
            seen.add(label)
            labels.append(label)
    return labels


def count_visible_items(value: Any) -> int:
    if isinstance(value, list):
        return sum(1 for item in value if has_visible_value(item))
    if isinstance(value, str):
        return len([line for line in value.replace(",", "\n").splitlines() if line.strip()])
    return 1 if has_visible_value(value) else 0


def nested_text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(nested_text_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(nested_text_values(item))
        return values
    if value is None:
        return []
    return [str(value)]


def normalized_phone_digits(value: str) -> str:
    digits = re.sub(r"\D+", "", value)
    if digits.startswith("0034") and len(digits) == 13:
        return digits[4:]
    if digits.startswith("34") and len(digits) == 11:
        return digits[2:]
    return digits


def proposal_phone_count(payload: dict[str, Any]) -> int:
    phones: set[str] = set()
    fields = proposed_fields(payload)
    for key in PHONE_FIELD_KEYS:
        if key not in fields:
            continue
        for value in nested_text_values(fields[key]):
            for candidate in PHONE_RE.findall(value):
                digits = normalized_phone_digits(candidate)
                if len(digits) == 9:
                    phones.add(digits)
            digits = normalized_phone_digits(value)
            if len(digits) == 9 and digits[:1] in {"6", "7", "8", "9"}:
                phones.add(digits)
    return len(phones)


def proposal_card_summary(card: dict[str, Any]) -> dict[str, Any]:
    payload = card.pop("payload", None)
    if not isinstance(payload, dict):
        return card
    fields = proposed_fields(payload)
    card["proposed_field_labels"] = proposal_field_labels(payload)
    card["proposed_locations_count"] = count_visible_items(fields.get("locations"))
    card["proposed_professionals_count"] = (
        count_visible_items(fields.get("profesionales"))
        or count_visible_items(fields.get("professionals"))
    )
    card["proposed_phone_count"] = proposal_phone_count(payload)
    return card


def summarize_backlog_report(report: dict[str, Any]) -> dict[str, Any]:
    for section in ("clinic_workgroups", "duplicate_enrichment"):
        for row in report.get(section) or []:
            cards = row.get("cards")
            if isinstance(cards, list):
                row["cards"] = [proposal_card_summary(card) for card in cards if isinstance(card, dict)]
    return report


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
          when review_type = 'clinic_claim_request' then 'reclamaciones de ficha'
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
        items.claim_request_reviews desc,
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
      count(*) filter (where review_type = 'clinic_claim_request') as claim_request_reviews,
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
          'payload', payload,
          'created_at', created_at,
          'updated_at', updated_at
        )
        order by
          case
            when review_type = 'clinic_quality_audit'
              and payload ->> 'quality_context' = 'blocking_claims' then 1
            when review_type = 'clinic_claim_request' then 2
            when review_type = 'source_change_detected' then 3
            when review_type = 'clinic_profile_enrichment' then 4
            when review_type = 'clinic_quality_audit' then 5
            when review_type = 'candidate_clinic' then 6
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
      claim_request_reviews desc,
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
    return summarize_backlog_report(json.loads(run_psql(sql, local_env)))


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
        "clinic_claim_request": "reclamación de ficha",
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
    if as_int(row.get("claim_request_reviews")):
        steps.append("reclamaciones")
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
    if as_int(row.get("claim_request_reviews")):
        return "escalar a Daniel antes de cambiar datos"
    if as_int(row.get("source_change_reviews")):
        return "primero revisar qué cambió en la fuente"
    if as_int(row.get("enrichment_reviews")):
        return "priorizar y resolver una propuesta cada vez"
    return "priorizar antes de cerrar"


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
        ("claim_request_reviews", "reclamación", "reclamaciones"),
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


def format_card_proposal_summary(card: dict[str, Any]) -> str:
    labels = [str(item) for item in card.get("proposed_field_labels") or [] if str(item).strip()]
    parts = []
    if labels:
        shown = labels[:5]
        suffix = f" +{len(labels) - 5}" if len(labels) > 5 else ""
        parts.append("campos: " + ", ".join(shown) + suffix)
    counts = []
    location_count = as_int(card.get("proposed_locations_count"))
    phone_count = as_int(card.get("proposed_phone_count"))
    professional_count = as_int(card.get("proposed_professionals_count"))
    if location_count:
        counts.append(f"{location_count} {plural(location_count, 'sede', 'sedes')}")
    if phone_count:
        counts.append(f"{phone_count} {plural(phone_count, 'teléfono', 'teléfonos')}")
    if professional_count:
        counts.append(f"{professional_count} {plural(professional_count, 'especialista', 'especialistas')}")
    if counts:
        parts.append("revisar: " + ", ".join(counts))
    return " · ".join(parts)


def format_workgroup_card(card: dict[str, Any]) -> str:
    title = card.get("title") or "Revisión abierta"
    review_type = review_type_label(card.get("review_type"))
    priority = as_int(card.get("priority"))
    created = parse_timestamp(card.get("created_at"))
    proposal_summary = format_card_proposal_summary(card)
    proposal_detail = f" · {proposal_summary}" if proposal_summary else ""
    return f"  - {title}: {review_type} · P{priority} · creada {created}{proposal_detail}"


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
    claim_workgroups = [
        row for row in workgroups if as_int(row.get("claim_request_reviews"))
    ]
    if claim_workgroups:
        first = claim_workgroups[0]
        name = first.get("clinic_name") or first.get("clinic_slug") or "la primera reclamación"
        return f"Revisar {name}: reclamación de ficha pendiente; Daniel decide antes de cambiar datos"
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
