#!/usr/bin/env python3
"""Read-only reconciliation for open Google Maps/review-link proposals."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from typing import Any
from urllib.parse import urlparse

from admin_digest import as_int, parse_timestamp
from google_maps_url_rules import google_maps_review_status, is_direct_google_maps_profile_url
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


MAP_KEYS = ("maps_url", "google_maps_url", "map_url")
REVIEW_KEYS = ("google_reviews_url", "reviews_url", "valoraciones_url")


STATUS_LABELS = {
    "direct_profile": "parece perfil directo de clínica",
    "search_or_route": "parece búsqueda o ruta; no guardar",
    "street_address": "parece dirección suelta; no guardar",
    "needs_manual_review": "necesita comprobación manual",
    "not_google_maps": "no parece Google Maps",
    "empty": "sin enlace",
}

DECISION_FIELD_LABELS = {
    "maps_url": "Google Maps",
    "google_reviews_url": "Valoraciones Google",
}


def compact_lookup_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return "".join(char for char in ascii_value if char.isalnum())


def compact_url(value: Any, limit: int = 110) -> str:
    clean = str(value or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def valid_http_url(value: Any) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values:
        clean = str(value or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result


def candidate_objects(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ("proposed_fields", "proposed_current_data", "fields", "candidate"):
        value = payload.get(key)
        if isinstance(value, dict):
            candidates.append(value)
    candidates.append(payload)
    return candidates


def links_from_object(value: Any, keys: tuple[str, ...]) -> list[str]:
    links: list[str] = []
    if isinstance(value, dict):
        for key in keys:
            if value.get(key):
                links.append(str(value[key]))
        locations = value.get("locations")
        if isinstance(locations, list):
            for location in locations:
                links.extend(links_from_object(location, keys))
    return links


def proposed_links(payload: dict[str, Any]) -> dict[str, list[str]]:
    maps: list[str] = []
    reviews: list[str] = []
    for value in candidate_objects(payload):
        maps.extend(links_from_object(value, MAP_KEYS))
        reviews.extend(links_from_object(value, REVIEW_KEYS))
    return {
        "maps": dedupe(maps),
        "reviews": dedupe(reviews),
    }


def source_urls(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    if isinstance(payload.get("source_urls"), list):
        values.extend(str(item) for item in payload["source_urls"])
    for key in ("source_url", "website", "web"):
        if payload.get(key):
            values.append(str(payload[key]))
    return dedupe(values)


def map_status_counts(urls: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for url in urls:
        status = google_maps_review_status(url)
        counts[status] = counts.get(status, 0) + 1
    return counts


def google_map_decision_item(url: str) -> dict[str, Any]:
    status = google_maps_review_status(url)
    direct = is_direct_google_maps_profile_url(url)
    return {
        "field": "maps_url",
        "label": DECISION_FIELD_LABELS["maps_url"],
        "url": url,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "direct_profile": direct,
        "safe_to_auto_publish": False,
        "manual_decision": "confirm_real_clinic_profile" if direct else "reject_or_replace_with_real_profile",
        "admin_action": (
            "abrir enlace y aprobar solo si es la ficha real de la clínica"
            if direct
            else "rechazar o modificar con el perfil real de Google Business"
        ),
    }


def google_review_decision_item(url: str) -> dict[str, Any]:
    return {
        "field": "google_reviews_url",
        "label": DECISION_FIELD_LABELS["google_reviews_url"],
        "url": url,
        "status": "review_link",
        "status_label": "enlace de valoraciones",
        "direct_profile": False,
        "safe_to_auto_publish": False,
        "manual_decision": "confirm_reviews_match_main_profile",
        "admin_action": "aprobar solo si pertenece a la misma ficha principal de Google Maps",
    }


def manual_decision_items(maps: list[str], reviews: list[str]) -> list[dict[str, Any]]:
    items = [google_map_decision_item(url) for url in maps]
    items.extend(google_review_decision_item(url) for url in reviews if valid_http_url(url))
    return items


def decision_field_labels(items: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for item in items:
        label = str(item.get("label") or "").strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def review_link_count(urls: list[str]) -> int:
    return len([url for url in urls if valid_http_url(url)])


def google_link_next_step(row: dict[str, Any]) -> str:
    maps = row.get("maps_urls") or []
    reviews = row.get("review_urls") or []
    direct_maps = [url for url in maps if is_direct_google_maps_profile_url(url)]
    unsafe_maps = [url for url in maps if url and not is_direct_google_maps_profile_url(url)]
    if direct_maps:
        return "abrir el enlace, confirmar que es la ficha real de la clínica y guardar solo tras revisión humana"
    if unsafe_maps:
        return "no guardar ese Maps; buscar el perfil real de Google Business de la clínica"
    if reviews:
        return "completar primero el perfil principal de Google Maps antes de guardar valoraciones"
    return "sin enlace útil; mantener Google Maps pendiente"


def reconcile_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    links = proposed_links(payload)
    maps = links["maps"]
    reviews = links["reviews"]
    result = {
        **row,
        "maps_urls": maps,
        "review_urls": reviews,
        "map_status_counts": map_status_counts(maps),
        "direct_map_count": len([url for url in maps if is_direct_google_maps_profile_url(url)]),
        "unsafe_map_count": len([url for url in maps if url and not is_direct_google_maps_profile_url(url)]),
        "review_link_count": review_link_count(reviews),
        "source_urls": source_urls(payload),
    }
    result["manual_decision_items"] = manual_decision_items(maps, reviews)
    result["manual_decision_count"] = len(result["manual_decision_items"])
    result["fields_to_review"] = decision_field_labels(result["manual_decision_items"])
    result.pop("payload", None)
    result["next_step"] = google_link_next_step(result)
    return result


def summarize_cards(cards: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "review_cards": len(cards),
        "cards_with_direct_maps": sum(1 for card in cards if as_int(card.get("direct_map_count")) > 0),
        "cards_with_unsafe_maps": sum(1 for card in cards if as_int(card.get("unsafe_map_count")) > 0),
        "cards_with_review_links": sum(1 for card in cards if as_int(card.get("review_link_count")) > 0),
        "manual_decision_items": sum(as_int(card.get("manual_decision_count")) for card in cards),
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
      lower(coalesce(c.slug, '')) = lower({literal})
      or c.slug ilike {like}
      or c.display_name ilike {like}
      or rq.title ilike {like}
      or regexp_replace(translate(lower(coalesce(c.slug, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact}
      or regexp_replace(translate(lower(coalesce(c.display_name, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact}
    )
"""


def load_reconciliation(query: str, limit: int, local_env: dict[str, str]) -> dict[str, Any]:
    capped_limit = max(1, min(100, int(limit)))
    query_filter = clinic_lookup_filter(query)
    sql = f"""
select jsonb_build_object(
  'query', {sql_literal(query.strip())},
  'generated_at', now(),
  'writes_data', false,
  'review_cards',
  coalesce(jsonb_agg(to_jsonb(items) order by items.priority desc, items.created_at asc), '[]'::jsonb)
)
from (
  select
    rq.id,
    rq.review_type,
    rq.title,
    rq.priority,
    rq.created_at,
    rq.updated_at,
    c.slug as clinic_slug,
    c.display_name as clinic_name,
    c.city,
    c.status as clinic_status,
    rq.payload
  from public.review_queue rq
  left join public.clinics c on c.id = rq.clinic_id
  where rq.status = 'open'
    and (
      rq.payload::text ilike '%maps_url%'
      or rq.payload::text ilike '%google_maps_url%'
      or rq.payload::text ilike '%google_reviews_url%'
      or rq.payload::text ilike '%reviews_url%'
      or rq.payload::text ilike '%valoraciones_url%'
    )
    {query_filter}
  order by rq.priority desc, rq.created_at asc
  limit {capped_limit}
) items;
"""
    raw = json.loads(run_psql(sql, local_env))
    rows = [reconcile_row(row) for row in raw.get("review_cards") or [] if isinstance(row, dict)]
    raw["review_cards"] = sorted(
        rows,
        key=lambda row: (
            -as_int(row.get("direct_map_count")),
            -as_int(row.get("review_link_count")),
            -as_int(row.get("priority")),
            str(row.get("created_at") or ""),
        ),
    )
    raw["summary"] = summarize_cards(raw["review_cards"])
    return raw


def first_status_label(counts: dict[str, int]) -> str:
    if not counts:
        return "sin Maps propuesto"
    order = ("direct_profile", "search_or_route", "street_address", "needs_manual_review", "not_google_maps", "empty")
    parts = []
    for key in order:
        count = as_int(counts.get(key))
        if count:
            parts.append(f"{STATUS_LABELS.get(key, key)}: {count}")
    return "; ".join(parts) if parts else "sin Maps propuesto"


def format_reconciliation(report: dict[str, Any]) -> str:
    cards = report.get("review_cards") or []
    lines = [
        "# Vitalarga Google link review reconciliation",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        f"Consulta: {report.get('query') or 'todas las tarjetas abiertas'}",
        "- Writes data: no",
        f"- Tarjetas: {as_int((report.get('summary') or {}).get('review_cards'))}",
        "",
    ]
    if not cards:
        lines.extend([
            "## Sin tarjetas",
            "- No he encontrado tarjetas abiertas con enlaces Google propuestos.",
        ])
        return "\n".join(lines) + "\n"

    for row in cards:
        clinic = row.get("clinic_name") or row.get("clinic_slug") or "sin clínica enlazada"
        title = row.get("title") or "Revisión interna"
        lines.extend([
            f"## {clinic}",
            f"- Tarjeta: {title}",
            f"- Estado Maps: {first_status_label(row.get('map_status_counts') or {})}",
            f"- Valoraciones Google: {as_int(row.get('review_link_count'))} enlace(s)",
            f"- Decisiones manuales: {', '.join(row.get('fields_to_review') or ['sin campo directo'])}",
            f"- Siguiente paso: {row.get('next_step')}",
        ])
        maps = row.get("maps_urls") or []
        if maps:
            lines.append("- Maps propuesto: " + ", ".join(compact_url(url) for url in maps[:2]))
        reviews = row.get("review_urls") or []
        if reviews:
            lines.append("- Valoraciones propuestas: " + ", ".join(compact_url(url) for url in reviews[:2]))
        sources = row.get("source_urls") or []
        if sources:
            lines.append("- Fuente: " + compact_url(sources[0]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_compact_reconciliation(report: dict[str, Any]) -> str:
    cards = [card for card in report.get("review_cards") or [] if isinstance(card, dict)]
    summary = report.get("summary") or {}
    lines = [
        "# Vitalarga Google link review reconciliation",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        f"Consulta: {report.get('query') or 'todas las tarjetas abiertas'}",
        "- Writes data: no",
        f"- Tarjetas: {as_int(summary.get('review_cards'))}",
        f"- Con perfil directo: {as_int(summary.get('cards_with_direct_maps'))}",
        f"- Con Maps dudoso: {as_int(summary.get('cards_with_unsafe_maps'))}",
        f"- Con valoraciones: {as_int(summary.get('cards_with_review_links'))}",
        f"- Decisiones manuales: {as_int(summary.get('manual_decision_items'))}",
        "",
        "## Primeras tarjetas",
    ]
    if not cards:
        lines.append("- No hay tarjetas abiertas con enlaces Google propuestos.")
        return "\n".join(lines) + "\n"
    for row in cards[:5]:
        clinic = row.get("clinic_name") or row.get("clinic_slug") or "sin clínica enlazada"
        title = row.get("title") or "Revisión interna"
        lines.append(
            f"- {clinic}: {title} · "
            f"{first_status_label(row.get('map_status_counts') or {})}; "
            f"{as_int(row.get('review_link_count'))} valoraciones · "
            f"campos: {', '.join(row.get('fields_to_review') or ['sin campo directo'])} · "
            f"{row.get('next_step')}"
        )
    lines.append("")
    lines.append("Nota: salida compacta sin URLs. Abre la tarjeta en el panel para revisar el enlace real.")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clinic", default="", help="Normal clinic name, slug or review-title fragment.")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    parser.add_argument("--compact", action="store_true", help="Print counts and next steps without URLs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    report = load_reconciliation(args.clinic, args.limit, load_env_file())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.compact:
        print(format_compact_reconciliation(report), end="")
    else:
        print(format_reconciliation(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
