#!/usr/bin/env python3
"""Read-only reconciliation for proposed specialists on visible clinics."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from typing import Any

from admin_digest import as_int, parse_timestamp
from measure_specialist_coverage import clean_specialist_example, plural, status_label
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


SPECIALIST_FIELD_PATHS = ("professionals.published", "team.public_professionals")
PUBLIC_STATUSES = ("published", "preliminary")


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def normalize_person_key(value: Any) -> str:
    clean = unicodedata.normalize("NFKD", str(value or ""))
    clean = clean.encode("ascii", "ignore").decode("ascii").lower()
    clean = clean.replace(".", " ")
    tokens = [
        token
        for token in "".join(char if char.isalnum() else " " for char in clean).split()
        if token not in {"dr", "dra", "doctor", "doctora", "prof", "profa"}
    ]
    return " ".join(tokens)


def clean_person_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [values]
    result: list[str] = []
    seen = set()
    for value in values:
        clean = clean_specialist_example(value)
        if not clean:
            continue
        key = normalize_person_key(clean)
        if not key or key in {"null", "none"} or key in seen:
            continue
        seen.add(key)
        result.append(clean)
    return result


def merge_people(*groups: list[str]) -> list[str]:
    result: list[str] = []
    seen = set()
    for group in groups:
        for person in group:
            key = normalize_person_key(person)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(person)
    return result


def review_card_people(card: dict[str, Any]) -> list[str]:
    return clean_person_list(card.get("professionals") or [])


def compact_url(value: Any, limit: int = 72) -> str:
    clean = str(value or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def review_people(row: dict[str, Any]) -> list[str]:
    people: list[str] = []
    for card in row.get("review_cards") or []:
        if isinstance(card, dict):
            people = merge_people(people, review_card_people(card))
    return people


def clean_urls(values: Any) -> list[str]:
    if not isinstance(values, list):
        values = [values]
    urls: list[str] = []
    seen = set()
    for value in values:
        clean = str(value or "").strip()
        if not clean or not clean.lower().startswith(("http://", "https://")):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(clean)
    return urls


def annotated_review_cards(cards: list[dict[str, Any]], published_keys: set[str]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for card in cards:
        people = review_card_people(card)
        pending = [
            person for person in people
            if normalize_person_key(person) not in published_keys
        ]
        already = [
            person for person in people
            if normalize_person_key(person) in published_keys
        ]
        annotated.append({
            **card,
            "professionals_clean": people,
            "professional_count": len(people),
            "pending_professionals_from_card": pending,
            "pending_professional_count": len(pending),
            "already_published_from_card": already,
            "already_published_count": len(already),
            "has_source_url": bool(str(card.get("source_url") or "").strip()),
        })
    return annotated


def reconcile_row(row: dict[str, Any]) -> dict[str, Any]:
    published = clean_person_list(row.get("published_professionals") or [])
    published_keys = {normalize_person_key(person) for person in published}
    review_cards = annotated_review_cards(
        [card for card in row.get("review_cards") or [] if isinstance(card, dict)],
        published_keys,
    )
    proposed = merge_people(*[card.get("professionals_clean") or [] for card in review_cards])
    internal = clean_person_list(row.get("claim_professionals") or [])
    claim_sources = clean_urls(row.get("claim_source_urls") or [])
    all_detected = merge_people(proposed, internal)
    pending = [person for person in all_detected if normalize_person_key(person) not in published_keys]
    already = [person for person in all_detected if normalize_person_key(person) in published_keys]
    result = {
        **row,
        "published_professionals_clean": published,
        "review_professionals_clean": proposed,
        "claim_professionals_clean": internal,
        "claim_source_urls_clean": claim_sources,
        "review_cards": review_cards,
        "pending_professionals": pending,
        "already_published_detected": already,
        "published_count": len(published),
        "review_card_count": len(review_cards),
        "review_professional_count": len(proposed),
        "claim_professional_count": len(internal),
        "claim_source_count": len(claim_sources),
        "pending_professional_count": len(pending),
    }
    result["next_step"] = specialist_reconciliation_next_step(result)
    return result


def specialist_reconciliation_next_step(row: dict[str, Any]) -> str:
    pending = as_int(row.get("pending_professional_count"))
    cards = as_int(row.get("review_card_count"))
    internal = as_int(row.get("claim_professional_count"))
    if pending and cards:
        return "abrir las tarjetas de especialistas, cargar nombres al formulario y guardar solo tras revisión humana"
    if pending and internal:
        return "preparar una propuesta revisable desde los nombres internos antes de tocar la ficha pública"
    if cards:
        return "abrir las tarjetas y comprobar si los especialistas ya están representados en la ficha"
    if internal:
        return "comprobar si los nombres internos ya están representados o necesitan propuesta"
    return "buscar una página pública de equipo antes de proponer especialistas"


def summarize_clinics(clinics: list[dict[str, Any]]) -> dict[str, int]:
    cards = [
        card
        for row in clinics
        for card in row.get("review_cards") or []
        if isinstance(card, dict)
    ]
    return {
        "clinics": len(clinics),
        "clinics_with_pending_professionals": sum(
            1 for row in clinics if as_int(row.get("pending_professional_count")) > 0
        ),
        "clinics_with_review_cards": sum(
            1 for row in clinics if as_int(row.get("review_card_count")) > 0
        ),
        "published_professionals": sum(as_int(row.get("published_count")) for row in clinics),
        "review_cards": sum(as_int(row.get("review_card_count")) for row in clinics),
        "review_professionals": sum(as_int(row.get("review_professional_count")) for row in clinics),
        "claim_professionals": sum(as_int(row.get("claim_professional_count")) for row in clinics),
        "claim_source_urls": sum(as_int(row.get("claim_source_count")) for row in clinics),
        "clinics_with_claim_sources": sum(
            1 for row in clinics if as_int(row.get("claim_source_count")) > 0
        ),
        "pending_professionals": sum(as_int(row.get("pending_professional_count")) for row in clinics),
        "review_cards_with_source": sum(1 for card in cards if card.get("has_source_url")),
        "review_cards_without_source": sum(1 for card in cards if not card.get("has_source_url")),
        "review_cards_with_pending_professionals": sum(
            1 for card in cards if as_int(card.get("pending_professional_count")) > 0
        ),
        "review_cards_already_represented": sum(
            1
            for card in cards
            if as_int(card.get("professional_count")) > 0
            and as_int(card.get("pending_professional_count")) == 0
        ),
    }


def clinic_lookup_filter(query: str) -> str:
    clean = query.strip()
    if not clean:
        return ""
    literal = sql_literal(clean)
    like = sql_literal(f"%{clean}%")
    compact = sql_literal(f"%{compact_lookup_key(clean)}%")
    return f"""
    and (
      lower(c.slug) = lower({literal})
      or c.slug ilike {like}
      or c.display_name ilike {like}
      or regexp_replace(translate(lower(coalesce(c.slug, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact}
      or regexp_replace(translate(lower(coalesce(c.display_name, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact}
    )
"""


def load_reconciliation(query: str, limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    capped_limit = max(1, min(100, int(limit)))
    query_filter = clinic_lookup_filter(query)
    status_list = ", ".join(sql_literal(status) for status in PUBLIC_STATUSES)
    field_path_list = ", ".join(sql_literal(path) for path in SPECIALIST_FIELD_PATHS)
    sql = f"""
with target_clinics as (
  select c.id, c.slug, c.display_name as clinic_name, c.city, c.status, c.current_data
  from public.clinics c
  where c.status in ({status_list})
  {query_filter}
  order by c.display_name
  limit {capped_limit}
),
published_names as (
  select
    c.id as clinic_id,
    coalesce(
      jsonb_agg(distinct btrim(person.value) order by btrim(person.value))
        filter (where btrim(person.value) <> ''),
      '[]'::jsonb
    ) as professionals
  from target_clinics c
  left join lateral jsonb_array_elements_text(
    case
      when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
        then c.current_data -> 'profesionales'
      else '[]'::jsonb
    end
  ) person(value) on true
  group by c.id
),
review_name_rows as (
  select
    rq.clinic_id,
    rq.id,
    rq.title,
    rq.priority,
    rq.created_at,
    coalesce(
      nullif(btrim(rq.payload ->> 'source_url'), ''),
      nullif(btrim(rq.payload #>> '{{source,source_url}}'), ''),
      nullif(btrim(rq.payload #>> '{{source,url}}'), ''),
      nullif(btrim(rq.payload #>> '{{candidate,source_url}}'), ''),
      nullif(btrim(rq.payload #>> '{{candidate,website}}'), ''),
      nullif(btrim(rq.payload #>> '{{candidate,web}}'), ''),
      nullif(btrim(rq.payload #>> '{{proposed_fields,source_url}}'), ''),
      ''
    ) as source_url,
    btrim(person.value) as person_name
  from public.review_queue rq
  join target_clinics c on c.id = rq.clinic_id
  cross join lateral jsonb_array_elements_text(
    (case when jsonb_typeof(rq.payload #> '{{candidate,profesionales}}') = 'array' then rq.payload #> '{{candidate,profesionales}}' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload #> '{{candidate,professionals}}') = 'array' then rq.payload #> '{{candidate,professionals}}' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload -> 'profesionales') = 'array' then rq.payload -> 'profesionales' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload #> '{{proposed_fields,profesionales}}') = 'array' then rq.payload #> '{{proposed_fields,profesionales}}' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload #> '{{proposed_fields,professionals}}') = 'array' then rq.payload #> '{{proposed_fields,professionals}}' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload #> '{{proposed_current_data,profesionales}}') = 'array' then rq.payload #> '{{proposed_current_data,profesionales}}' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload #> '{{fields,profesionales}}') = 'array' then rq.payload #> '{{fields,profesionales}}' else '[]'::jsonb end) ||
    (case when jsonb_typeof(rq.payload #> '{{fields,professionals}}') = 'array' then rq.payload #> '{{fields,professionals}}' else '[]'::jsonb end)
  ) person(value)
  where rq.status = 'open'
    and rq.review_type in ('candidate_clinic', 'clinic_profile_enrichment')
    and btrim(person.value) <> ''
),
review_cards as (
  select
    clinic_id,
    jsonb_agg(
      jsonb_build_object(
        'id', id,
        'title', title,
        'priority', priority,
        'created_at', created_at,
        'source_url', source_url,
        'professionals', professionals
      )
      order by jsonb_array_length(professionals) desc, priority desc, created_at asc
    ) as data
  from (
    select
      clinic_id,
      id,
      title,
      priority,
      created_at,
      source_url,
      coalesce(
        jsonb_agg(distinct person_name order by person_name) filter (where person_name <> ''),
        '[]'::jsonb
      ) as professionals
    from review_name_rows
    group by clinic_id, id, title, priority, created_at, source_url
  ) rows
  group by clinic_id
),
claim_name_rows as (
  select
    fc.clinic_id,
    btrim(person.value) as person_name,
    sr.source_url
  from public.field_claims fc
  join target_clinics c on c.id = fc.clinic_id
  left join public.source_records sr on sr.id = fc.source_record_id
  cross join lateral jsonb_array_elements_text(
    case
      when jsonb_typeof(fc.value) = 'array' then fc.value
      when jsonb_typeof(fc.value) = 'string' then jsonb_build_array(fc.value)
      when jsonb_typeof(fc.value) = 'object' and fc.value ? 'name' then jsonb_build_array(fc.value -> 'name')
      when jsonb_typeof(fc.value) = 'object' and fc.value ? 'full_name' then jsonb_build_array(fc.value -> 'full_name')
      when jsonb_typeof(fc.value) = 'object' and fc.value ? 'nombre' then jsonb_build_array(fc.value -> 'nombre')
      else '[]'::jsonb
    end
  ) person(value)
  where fc.field_path in ({field_path_list})
    and coalesce(fc.verification_status, '') not in ('rejected', 'stale', 'conflict')
    and btrim(person.value) <> ''
    and btrim(person.value) <> 'null'
),
claim_names as (
  select
    clinic_id,
    coalesce(
      jsonb_agg(distinct person_name order by person_name)
        filter (where person_name <> '' and person_name <> 'null'),
      '[]'::jsonb
    ) as professionals,
    coalesce(
      jsonb_agg(distinct btrim(source_url) order by btrim(source_url))
        filter (where btrim(coalesce(source_url, '')) <> ''),
      '[]'::jsonb
    ) as source_urls
  from claim_name_rows
  group by clinic_id
),
clinic_items as (
  select
    c.slug,
    c.clinic_name,
    c.city,
    c.status,
    coalesce(p.professionals, '[]'::jsonb) as published_professionals,
    coalesce(r.data, '[]'::jsonb) as review_cards,
    coalesce(cl.professionals, '[]'::jsonb) as claim_professionals,
    coalesce(cl.source_urls, '[]'::jsonb) as claim_source_urls
  from target_clinics c
  left join published_names p on p.clinic_id = c.id
  left join review_cards r on r.clinic_id = c.id
  left join claim_names cl on cl.clinic_id = c.id
)
select jsonb_build_object(
  'query', {sql_literal(query.strip())},
  'generated_at', now(),
  'writes_data', false,
  'clinics', coalesce(jsonb_agg(to_jsonb(clinic_items) order by clinic_name), '[]'::jsonb)
)
from clinic_items;
"""
    raw = json.loads(run_psql(sql, local_env))
    raw["clinics"] = sorted(
        [reconcile_row(row) for row in raw.get("clinics") or [] if isinstance(row, dict)],
        key=lambda row: (
            -as_int(row.get("pending_professional_count")),
            -as_int(row.get("review_card_count")),
            row.get("clinic_name") or row.get("slug") or "",
        ),
    )
    raw["summary"] = summarize_clinics(raw["clinics"])
    return raw


def compact_people(values: list[str], limit: int = 6) -> str:
    if not values:
        return "—"
    shown = values[:limit]
    suffix = f" +{len(values) - len(shown)}" if len(values) > len(shown) else ""
    return ", ".join(shown) + suffix


def format_review_cards(cards: list[dict[str, Any]], limit: int = 4) -> list[str]:
    lines = []
    for card in cards[:limit]:
        people = card.get("professionals_clean") or review_card_people(card)
        title = card.get("title") or "Revisión interna"
        count = as_int(card.get("professional_count")) or len(people)
        pending = as_int(card.get("pending_professional_count"))
        already = as_int(card.get("already_published_count"))
        source = compact_url(card.get("source_url"))
        source_note = f" · fuente: {source}" if source else " · fuente: pendiente"
        review_note = (
            f" · nuevos: {pending}; ya en ficha: {already}"
            if pending or already
            else ""
        )
        lines.append(
            f"  - {title}: {count} {plural(count, 'nombre', 'nombres')} ({compact_people(people, 4)}){review_note}{source_note}"
        )
    if len(cards) > limit:
        lines.append(f"  - +{len(cards) - limit} tarjetas más")
    return lines


def format_reconciliation(report: dict[str, Any]) -> str:
    clinics = report.get("clinics") or []
    summary = report.get("summary") or {}
    lines = [
        "# Vitalarga specialist reconciliation",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        f"Consulta: {report.get('query') or 'todas las fichas visibles'}",
        "- Writes data: no",
        f"- Clínicas medidas: {as_int(summary.get('clinics') or len(clinics))}",
        f"- Pendientes de decidir: {as_int(summary.get('pending_professionals'))}",
        f"- Tarjetas con especialistas: {as_int(summary.get('review_cards'))}",
        f"- Tarjetas con fuente clara: {as_int(summary.get('review_cards_with_source'))}/{as_int(summary.get('review_cards'))}",
        f"- Fuentes internas de especialistas: {as_int(summary.get('claim_source_urls'))}",
        f"- Tarjetas con nombres nuevos: {as_int(summary.get('review_cards_with_pending_professionals'))}",
        "",
    ]
    if not clinics:
        lines.extend([
            "## Sin resultados",
            "- No he encontrado fichas visibles con esa búsqueda.",
        ])
        return "\n".join(lines) + "\n"

    for row in clinics:
        name = row.get("clinic_name") or row.get("slug") or "Clínica sin nombre"
        city = row.get("city") or "sin ciudad"
        cards = row.get("review_cards") or []
        pending = row.get("pending_professionals") or []
        already = row.get("already_published_detected") or []
        claim_sources = row.get("claim_source_urls_clean") or []
        lines.extend([
            f"## {name}",
            f"- Ciudad/estado: {city} · {status_label(str(row.get('status') or ''))}",
            f"- Publicados en ficha: {as_int(row.get('published_count'))}",
            f"- En tarjetas abiertas: {as_int(row.get('review_professional_count'))} nombres en {as_int(row.get('review_card_count'))} tarjetas",
            f"- En evidencias internas: {as_int(row.get('claim_professional_count'))} nombres",
            f"- Fuentes internas: {compact_people([compact_url(url) for url in claim_sources], 3)}",
            f"- Pendientes de decidir: {as_int(row.get('pending_professional_count'))}",
            f"- Siguiente paso: {row.get('next_step')}",
            f"- Pendientes: {compact_people(pending)}",
        ])
        if already:
            lines.append(f"- Ya representados: {compact_people(already)}")
        if cards:
            lines.append("- Tarjetas:")
            lines.extend(format_review_cards(cards))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic", default="", help="Normal clinic name or slug.")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_reconciliation(args.clinic, args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_reconciliation(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
