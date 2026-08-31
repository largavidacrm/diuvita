#!/usr/bin/env python3
"""Read-only consolidation report for duplicate profile-enrichment reviews.

The script helps Daniel work one clinic case at a time. It merges open
clinic_profile_enrichment cards for the same clinic into one proposed field set,
keeps all source URLs, and flags scalar conflicts. It never edits clinics,
resolves review cards or publishes the website.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from typing import Any

from admin_digest import as_int, parse_timestamp, plural
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


FIELD_ALIASES = {
    "name": "display_name",
    "web": "website",
    "phone": "telefono",
    "telephone": "telefono",
    "google_maps_url": "maps_url",
    "reviews_url": "google_reviews_url",
    "professionals": "profesionales",
}

FIELD_LABELS = {
    "display_name": "Nombre",
    "website": "Web oficial",
    "country": "Pais",
    "city": "Ciudad",
    "region": "Region",
    "address": "Direccion",
    "maps_url": "Google Maps",
    "google_reviews_url": "Valoraciones Google",
    "summary": "Resumen",
    "services": "Servicios",
    "specialties": "Especialidades",
    "unidades": "Unidades",
    "profesionales": "Especialistas",
    "tech": "Tecnologia",
    "email": "Email",
    "telefono": "Telefono principal",
    "phone_fixed": "Telefono fijo",
    "phone_mobile": "Movil",
    "phone_whatsapp": "WhatsApp",
    "instagram": "Instagram",
    "years_in_practice": "Anios en ejercicio",
    "specialists_count": "Numero de especialistas",
    "team_credentialing_visible": "Colegiacion visible",
    "public_pricing": "Precio publico",
    "pricing_url": "Fuente de precios",
    "locations": "Sedes",
}

LIST_FIELDS = {"services", "specialties", "unidades", "profesionales", "locations", "tech"}
PHONE_FIELDS = {"telefono", "phone_fixed", "phone_mobile", "phone_whatsapp"}
PHONE_CANDIDATE_RE = re.compile(r"(?:\+34|0034|34)?[\s().-]*[6789](?:[\s().-]*\d){8}")
PROFILE_ALIASES = {
    "display_name": ("display_name", "name", "canonical_name"),
    "website": ("website", "web"),
    "telefono": ("telefono", "phone", "telephone"),
    "maps_url": ("maps_url", "google_maps_url"),
    "google_reviews_url": ("google_reviews_url", "reviews_url", "valoraciones_url"),
    "profesionales": ("profesionales", "professionals"),
}


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def normalize_space(value: Any) -> str:
    return " ".join(str(value or "").split())


def canonical_field(key: Any) -> str:
    clean = str(key or "").strip()
    return FIELD_ALIASES.get(clean, clean)


def field_label(key: Any) -> str:
    clean = canonical_field(key)
    return FIELD_LABELS.get(clean, clean.replace("_", " "))


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def value_key(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(
            {str(key): value_key(val) for key, val in sorted(value.items()) if not is_empty(val)},
            ensure_ascii=False,
            sort_keys=True,
        )
    if isinstance(value, list):
        return json.dumps(sorted(value_key(item) for item in value), ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return compact_lookup_key(normalize_space(value))


def phone_digits(value: Any) -> str:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if digits.startswith("0034") and len(digits) == 13:
        return digits[4:]
    if digits.startswith("34") and len(digits) == 11:
        return digits[2:]
    return digits


def plausible_phone(value: Any) -> bool:
    digits = phone_digits(value)
    return len(digits) == 9 and digits[0] in {"6", "7", "8", "9"}


def split_spanish_phones(value: Any) -> list[str]:
    raw = str(value or "")
    phones: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        digits = phone_digits(candidate)
        if not plausible_phone(digits) or digits in seen:
            return
        seen.add(digits)
        phones.append(digits)

    for match in PHONE_CANDIDATE_RE.finditer(raw):
        add(match.group(0))

    compact = "".join(char for char in raw if char.isdigit())
    if not phones and len(compact) > 9 and len(compact) % 9 == 0:
        for index in range(0, len(compact), 9):
            add(compact[index : index + 9])

    return phones


def phone_target_field(phone: Any, fallback_field: str) -> str:
    digits = phone_digits(phone)
    if digits.startswith(("8", "9")) and fallback_field != "phone_fixed":
        return "phone_fixed"
    if digits.startswith(("6", "7")) and fallback_field != "phone_mobile":
        return "phone_mobile"
    return ""


def expanded_phone_fields(field: str, value: Any) -> list[tuple[str, str]]:
    if field not in PHONE_FIELDS:
        return []
    phones = split_spanish_phones(value)
    if len(phones) < 2:
        return []
    fields = [(field, phones[0])]
    used_fields = {field}
    used_phones = {phones[0]}
    for phone in phones[1:]:
        target = phone_target_field(phone, field)
        if not target or target in used_fields or phone in used_phones:
            continue
        used_fields.add(target)
        used_phones.add(phone)
        fields.append((target, phone))
    return fields if len(fields) > 1 else []


def location_key(value: Any) -> str:
    if isinstance(value, dict):
        parts = [
            value.get("name"),
            value.get("city"),
            value.get("address"),
            value.get("maps_url") or value.get("google_maps_url"),
            value.get("google_reviews_url") or value.get("reviews_url"),
        ]
        return "|".join(value_key(part) for part in parts if not is_empty(part))
    return value_key(value)


def list_items(value: Any, field: str) -> list[Any]:
    if is_empty(value):
        return []
    if isinstance(value, list):
        rows: list[Any] = []
        for item in value:
            rows.extend(list_items(item, field) if isinstance(item, list) else [item])
        return [item for item in rows if not is_empty(item)]
    if isinstance(value, tuple):
        return list_items(list(value), field)
    if isinstance(value, str):
        separators = ["\r\n", "\n", ";"]
        text = value
        for separator in separators:
            text = text.replace(separator, "\n")
        return [normalize_space(part) for part in text.split("\n") if normalize_space(part)]
    return [value]


def proposed_fields(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("proposed_fields", "proposed_current_data", "fields"):
        raw = payload.get(key)
        if isinstance(raw, dict):
            return raw
    return {}


def source_urls(payload: dict[str, Any]) -> list[str]:
    raw_values = [
        payload.get("source_url"),
        payload.get("source_urls"),
        payload.get("sources"),
        payload.get("candidate_source_url"),
    ]
    urls: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        if isinstance(raw, list):
            for item in raw:
                add(item)
            return
        url = normalize_space(raw)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    for raw in raw_values:
        add(raw)
    return urls


def merge_fields(cards: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, list[str]]]:
    merged: dict[str, Any] = {}
    seen_list_values: dict[str, set[str]] = {}
    scalar_variants: dict[str, list[dict[str, Any]]] = {}
    field_sources: dict[str, list[str]] = {}

    def add_field_source(field: str, review_id: Any) -> None:
        clean_review_id = str(review_id or "").strip()
        if not clean_review_id:
            return
        field_sources.setdefault(field, [])
        if clean_review_id not in field_sources[field]:
            field_sources[field].append(clean_review_id)

    def add_scalar_variant(field: str, value: Any, review_id: Any) -> None:
        add_field_source(field, review_id)
        key = value_key(value)
        scalar_variants.setdefault(field, [])
        if not any(item["key"] == key for item in scalar_variants[field]):
            scalar_variants[field].append({
                "key": key,
                "value": value,
                "review_ids": [str(review_id)] if review_id else [],
            })
        else:
            for item in scalar_variants[field]:
                if item["key"] == key and review_id:
                    item["review_ids"].append(str(review_id))
        if field not in merged:
            merged[field] = value

    for card in cards:
        payload = card.get("payload") if isinstance(card.get("payload"), dict) else {}
        review_id = card.get("id")
        for raw_key, raw_value in proposed_fields(payload).items():
            field = canonical_field(raw_key)
            if is_empty(raw_value):
                continue
            split_phone_fields = expanded_phone_fields(field, raw_value)
            if split_phone_fields:
                for phone_field, phone_value in split_phone_fields:
                    add_scalar_variant(phone_field, phone_value, review_id)
                continue
            add_field_source(field, review_id)
            if field in LIST_FIELDS:
                merged.setdefault(field, [])
                seen_list_values.setdefault(field, set())
                for item in list_items(raw_value, field):
                    key = location_key(item) if field == "locations" else value_key(item)
                    if not key or key in seen_list_values[field]:
                        continue
                    seen_list_values[field].add(key)
                    merged[field].append(item)
                continue

            add_scalar_variant(field, raw_value, review_id)

    conflicts = [
        {
            "field": field,
            "label": field_label(field),
            "kept_value": variants[0]["value"],
            "variant_count": len(variants),
            "values": [variant["value"] for variant in variants],
            "review_ids": sorted({rid for variant in variants for rid in variant.get("review_ids", [])}),
        }
        for field, variants in sorted(scalar_variants.items())
        if len(variants) > 1
    ]
    return merged, conflicts, field_sources


def profile_value(group: dict[str, Any], field: str) -> Any:
    current_data = group.get("current_data") if isinstance(group.get("current_data"), dict) else {}
    aliases = PROFILE_ALIASES.get(field, (field,))
    for alias in aliases:
        if alias in current_data and not is_empty(current_data[alias]):
            return current_data[alias]
    if field == "display_name":
        return group.get("clinic_name")
    for alias in aliases:
        if alias in group and not is_empty(group[alias]):
            return group[alias]
    return None


def field_already_present(group: dict[str, Any], field: str, value: Any) -> bool:
    existing = profile_value(group, field)
    if is_empty(existing) or is_empty(value):
        return False
    if field in LIST_FIELDS:
        existing_keys = {
            location_key(item) if field == "locations" else value_key(item)
            for item in list_items(existing, field)
        }
        proposed_keys = [
            location_key(item) if field == "locations" else value_key(item)
            for item in list_items(value, field)
        ]
        return bool(proposed_keys) and all(key in existing_keys for key in proposed_keys)
    return value_key(existing) == value_key(value)


def field_count(value: Any, field: str) -> int:
    if field in LIST_FIELDS:
        return len(list_items(value, field))
    return 0 if is_empty(value) else 1


def consolidated_group(group: dict[str, Any]) -> dict[str, Any]:
    cards = [card for card in group.get("cards") or [] if isinstance(card, dict)]
    merged_fields, conflicts, field_sources = merge_fields(cards)
    source_seen: set[str] = set()
    sources: list[str] = []
    for card in cards:
        payload = card.get("payload") if isinstance(card.get("payload"), dict) else {}
        for url in source_urls(payload):
            if url not in source_seen:
                source_seen.add(url)
                sources.append(url)

    already_present = sorted(
        field for field, value in merged_fields.items() if field_already_present(group, field, value)
    )
    review_fields = sorted(field for field in merged_fields if field not in already_present)
    merged_field_counts = {
        field: field_count(value, field)
        for field, value in sorted(merged_fields.items())
    }
    conflict_fields = [item["field"] for item in conflicts]
    weak_phone_fields = sorted(
        field
        for field, value in merged_fields.items()
        if field in PHONE_FIELDS and not plausible_phone(value)
    )
    if conflicts:
        next_step = "resolver conflictos antes de validar propuestas"
    elif weak_phone_fields:
        next_step = "revisar telefonos dudosos antes de validar propuestas"
    elif review_fields:
        next_step = "abrir el caso y resolver una propuesta cada vez"
    else:
        next_step = "confirmar que la ficha ya lo contiene y cerrar tarjetas sobrantes"

    return {
        "clinic_id": group.get("clinic_id"),
        "clinic_slug": group.get("clinic_slug"),
        "clinic_name": group.get("clinic_name"),
        "city": group.get("city"),
        "clinic_status": group.get("clinic_status"),
        "card_count": len(cards),
        "source_count": len(sources),
        "source_urls": sources,
        "merged_fields": merged_fields,
        "merged_field_count": len(merged_fields),
        "merged_field_counts": merged_field_counts,
        "review_fields": review_fields,
        "already_present_fields": already_present,
        "already_present_count": len(already_present),
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "conflict_fields": conflict_fields,
        "weak_phone_count": len(weak_phone_fields),
        "weak_phone_fields": weak_phone_fields,
        "field_review_ids": field_sources,
        "next_step": next_step,
    }


def load_duplicate_groups(limit: int, clinic_query: str, local_env: dict[str, str]) -> list[dict[str, Any]]:
    clean_query = clinic_query.strip()
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
with open_enrichment as (
  select
    rq.id,
    rq.clinic_id,
    rq.title,
    rq.priority,
    rq.payload,
    rq.created_at,
    rq.updated_at,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.website,
    c.country,
    c.city,
    c.region,
    c.address,
    c.status as clinic_status,
    c.current_data
  from public.review_queue rq
  join public.clinics c on c.id = rq.clinic_id
  where rq.status = 'open'
    and rq.review_type = 'clinic_profile_enrichment'
    and rq.clinic_id is not null
    and {clinic_filter}
),
duplicate_groups as (
  select
    clinic_id,
    max(clinic_slug) as clinic_slug,
    max(clinic_name) as clinic_name,
    max(website) as website,
    max(country) as country,
    max(city) as city,
    max(region) as region,
    max(address) as address,
    max(clinic_status) as clinic_status,
    jsonb_agg(current_data order by priority desc, created_at asc) -> 0 as current_data,
    count(*) as card_count,
    max(priority) as max_priority,
    min(created_at) as oldest_created_at,
    jsonb_agg(
      jsonb_build_object(
        'id', id,
        'title', title,
        'priority', priority,
        'payload', payload,
        'created_at', created_at,
        'updated_at', updated_at
      )
      order by priority desc, created_at asc
    ) as cards
  from open_enrichment
  group by clinic_id
  having count(*) > 1
)
select coalesce(jsonb_agg(to_jsonb(items) order by items.card_count desc, items.max_priority desc, items.oldest_created_at asc), '[]'::jsonb)
from (
  select *
  from duplicate_groups
  order by card_count desc, max_priority desc, oldest_created_at asc
  limit {max(1, min(50, int(limit)))}
) items;
"""
    return json.loads(run_psql(sql, local_env) or "[]")


def build_report(groups: list[dict[str, Any]], clinic_query: str = "") -> dict[str, Any]:
    consolidated = [consolidated_group(group) for group in groups]
    return {
        "mode": "read_only",
        "writes_data": False,
        "clinic_query": clinic_query.strip(),
        "summary": {
            "groups": len(consolidated),
            "cards": sum(as_int(group.get("card_count")) for group in consolidated),
            "merged_fields": sum(as_int(group.get("merged_field_count")) for group in consolidated),
            "fields_to_review": sum(len(group.get("review_fields") or []) for group in consolidated),
            "already_present_fields": sum(as_int(group.get("already_present_count")) for group in consolidated),
            "conflicts": sum(as_int(group.get("conflict_count")) for group in consolidated),
            "groups_with_conflicts": sum(1 for group in consolidated if as_int(group.get("conflict_count"))),
            "weak_phone_fields": sum(as_int(group.get("weak_phone_count")) for group in consolidated),
            "groups_with_weak_phone": sum(1 for group in consolidated if as_int(group.get("weak_phone_count"))),
        },
        "groups": consolidated,
    }


def format_field_list(fields: list[str]) -> str:
    if not fields:
        return "ninguno"
    return ", ".join(field_label(field) for field in fields)


def format_group(group: dict[str, Any]) -> str:
    name = group.get("clinic_name") or group.get("clinic_slug") or "sin clinica"
    cards = as_int(group.get("card_count"))
    conflicts = as_int(group.get("conflict_count"))
    sources = as_int(group.get("source_count"))
    fields = as_int(group.get("merged_field_count"))
    review_fields = group.get("review_fields") or []
    already_present = group.get("already_present_fields") or []
    lines = [
        (
            f"- {name}: {cards} {plural(cards, 'tarjeta', 'tarjetas')} -> "
            f"{fields} {plural(fields, 'campo fusionado', 'campos fusionados')}, "
            f"{sources} {plural(sources, 'fuente', 'fuentes')}, "
            f"{conflicts} {plural(conflicts, 'conflicto', 'conflictos')}"
        ),
        f"  siguiente: {group.get('next_step')}",
        f"  revisar: {format_field_list(review_fields)}",
    ]
    if already_present:
        lines.append(f"  ya en ficha: {format_field_list(already_present)}")
    if conflicts:
        conflict_labels = ", ".join(field_label(item.get("field")) for item in group.get("conflicts") or [])
        lines.append(f"  conflictos: {conflict_labels}")
    weak_phone_fields = group.get("weak_phone_fields") or []
    if weak_phone_fields:
        lines.append(f"  telefonos dudosos: {format_field_list(weak_phone_fields)}")
    return "\n".join(lines)


def format_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    groups = report.get("groups") or []
    lines = [
        "# Vitalarga: consolidacion de mejoras",
        "",
        f"- Grupos duplicados: {as_int(summary.get('groups'))}",
        f"- Tarjetas implicadas: {as_int(summary.get('cards'))}",
        f"- Campos fusionados: {as_int(summary.get('merged_fields'))}",
        f"- Campos a revisar: {as_int(summary.get('fields_to_review'))}",
        f"- Campos que ya parecen estar en ficha: {as_int(summary.get('already_present_fields'))}",
        f"- Conflictos: {as_int(summary.get('conflicts'))}",
        f"- Telefonos dudosos: {as_int(summary.get('weak_phone_fields'))}",
        "- Writes data: no",
        "",
        "## Grupos",
    ]
    if not groups:
        lines.append("- No hay mejoras duplicadas abiertas.")
    for group in groups:
        lines.append(format_group(group))
    lines.extend([
        "",
        "Nota: este informe no resuelve tarjetas. Sirve para priorizar revisiones, detectar conflictos y preparar campos antes de decidir tarjetas una a una.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--clinic", default="", help="Clinic name or slug to focus.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    groups = load_duplicate_groups(args.limit, args.clinic, load_env_file())
    report = build_report(groups, args.clinic)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
