#!/usr/bin/env python3
"""Build read-only one-decision packets from open clinic review proposals."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from google_maps_url_rules import google_maps_review_status
from review_backlog_brief import (
    compact_lookup_key,
    count_visible_items,
    field_label,
    has_visible_value,
    nested_text_values,
    normalized_phone_digits,
    proposed_fields,
)
from submit_discovery_candidates import load_env_file, run_psql, sql_literal


PACKET_SCHEMA_VERSION = "review_decision_packet.v1"
DECISION_ACTIONS = ["approve", "reject", "modify"]
FIELD_ALIASES = {
    "name": "display_name",
    "web": "website",
    "phone": "telefono",
    "telephone": "telefono",
    "google_maps_url": "maps_url",
    "reviews_url": "google_reviews_url",
    "professionals": "profesionales",
}
FIELD_ORDER = [
    "display_name",
    "website",
    "country",
    "city",
    "region",
    "address",
    "locations",
    "maps_url",
    "google_reviews_url",
    "summary",
    "services",
    "specialties",
    "unidades",
    "profesionales",
    "years_in_practice",
    "specialists_count",
    "team_credentialing_visible",
    "public_pricing",
    "pricing_url",
    "tech",
    "email",
    "telefono",
    "phone_fixed",
    "phone_mobile",
    "phone_whatsapp",
    "instagram",
]
ADMIN_FIELD_TARGETS = [
    (("summary", "resumen"), "summary", "Resumen", "clinicSummary"),
    (("website", "web"), "website", "Web oficial", "clinicWebsite"),
    (("address", "direcci", "sede"), "address", "Dirección", "clinicAddress"),
    (("maps", "google maps"), "maps_url", "Google Maps", "clinicMapsUrl"),
    (("reviews", "valoraciones", "reseñas", "resenas"), "google_reviews_url", "Valoraciones Google", "clinicGoogleReviewsUrl"),
    (("contact", "contacto", "tel", "phone", "telefono", "email"), "email", "Contacto público", "clinicEmail"),
    (("contact", "contacto", "tel", "phone", "telefono"), "telefono", "Teléfono principal", "clinicPhone"),
    (("service", "servicio"), "services", "Servicios", "clinicServices"),
    (("specialt", "especialidad"), "specialties", "Especialidades", "clinicSpecialties"),
    (("unit", "unidad"), "unidades", "Unidades", "clinicUnits"),
    (("professional", "profesional", "specialist", "especialista"), "profesionales", "Especialistas publicados", "clinicProfessionals"),
    (("technology", "tecnolog"), "tech", "Tecnología", "clinicTech"),
    (("years", "años", "anos", "trayectoria", "ejercicio"), "years_in_practice", "Años en ejercicio", "clinicYearsInPractice"),
    (("count", "numero de especialistas", "número de especialistas", "num specialists"), "specialists_count", "Número de especialistas", "clinicSpecialistsCount"),
    (("credential", "colegi"), "team_credentialing_visible", "Colegiación visible", "clinicTeamCredentialingVisible"),
    (("price", "precio", "tarifa"), "public_pricing", "Precio público", "clinicPublicPricing"),
]
REVIEW_TYPE_LABELS = {
    "candidate_clinic": "Clínica nueva",
    "clinic_profile_enrichment": "Mejora de ficha",
    "blocking_claim_review": "Claim bloqueante",
    "clinic_claim_request": "Reclamación de ficha",
    "clinic_quality_audit": "Revisión manual",
    "source_change_detected": "Cambio de fuente",
    "specialist_review": "Especialistas",
}
PHONE_FIELDS = {"telefono", "phone_fixed", "phone_mobile", "phone_whatsapp"}
SENSITIVE_FIELDS = {"public_pricing", "pricing_url", "team_credentialing_visible", "profesionales"}
SYNTHETIC_PREFIXES = ("quality_issue", "source_change")
GOOGLE_MAPS_STATUS_LABELS = {
    "direct_profile": "Parece perfil directo; confirmar clínica",
    "search_or_route": "No guardar tal cual: parece búsqueda o ruta",
    "street_address": "No guardar tal cual: parece dirección suelta",
    "needs_manual_review": "Revisar manualmente antes de guardar",
    "not_google_maps": "No parece Google Maps",
    "empty": "Sin enlace",
}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.I)
URL_RE = re.compile(r"https?://[^\s)>\]]+", flags=re.I)
PHONE_TEXT_RE = re.compile(r"(?:\+34|0034|34)?[\s().-]*[6789](?:[\s().-]*\d){8}")


def canonical_field(key: Any) -> str:
    clean = str(key or "").strip()
    return FIELD_ALIASES.get(clean, clean)


def review_type_label(value: Any) -> str:
    return REVIEW_TYPE_LABELS.get(str(value or ""), str(value or "Revisión").replace("_", " "))


def review_display_title(row: dict[str, Any]) -> str:
    title = str(row.get("title") or "").strip() or "Revisión abierta"
    if row.get("review_type") == "clinic_quality_audit":
        return re.sub(r"^Completar ficha:", "Revisión manual:", title, flags=re.I)
    return title


def is_synthetic_field(key: Any) -> bool:
    clean = canonical_field(key)
    return clean == "claim_request" or any(clean.startswith(prefix) for prefix in SYNTHETIC_PREFIXES)


def candidate_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = payload.get("candidate")
    return candidate if isinstance(candidate, dict) else payload


def value_kind(value: Any) -> str:
    if not has_visible_value(value):
        return "empty"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "text"


def value_count(value: Any) -> int:
    if isinstance(value, list):
        return count_visible_items(value)
    if isinstance(value, dict):
        return 1 if has_visible_value(value) else 0
    if isinstance(value, str) and "\n" in value:
        return count_visible_items(value)
    return 1 if has_visible_value(value) else 0


def value_packet(value: Any, include_values: bool) -> dict[str, Any]:
    packet = {
        "present": has_visible_value(value),
        "kind": value_kind(value),
        "count": value_count(value),
    }
    if include_values:
        packet["value"] = value
    return packet


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def redacted_text(value: Any, include_values: bool) -> str:
    clean = str(value or "").strip()
    if include_values:
        return clean
    clean = URL_RE.sub("[url]", clean)
    clean = EMAIL_RE.sub("[email]", clean)
    return PHONE_TEXT_RE.sub("[telefono]", clean)


def manual_review_targets_for_text(value: Any) -> list[dict[str, str]]:
    haystack = str(value or "").lower()
    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    for needles, key, label, admin_target_id in ADMIN_FIELD_TARGETS:
        if key in seen:
            continue
        if any(needle in haystack for needle in needles):
            seen.add(key)
            targets.append({
                "key": key,
                "label": label,
                "admin_target_id": admin_target_id,
            })
    return targets


def field_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        values: list[Any] = []
        for item in value:
            values.extend(field_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(field_values(item))
        return values
    return [value]


def clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def current_field_value(clinic: dict[str, Any], key: str) -> Any:
    data = clinic.get("current_data") if isinstance(clinic.get("current_data"), dict) else {}
    clean = canonical_field(key)
    direct = {
        "display_name": clinic.get("display_name") or data.get("name") or data.get("display_name"),
        "website": clinic.get("website") or data.get("web") or data.get("website"),
        "country": clinic.get("country") or data.get("country"),
        "city": clinic.get("city") or data.get("city"),
        "region": clinic.get("region") or data.get("region"),
        "address": clinic.get("address") or data.get("address"),
        "summary": clinic.get("summary") or data.get("summary"),
        "status": clinic.get("status") or data.get("status"),
    }
    if clean in direct:
        return direct[clean]
    if clean == "locations":
        return data.get("locations")
    for raw, canonical in FIELD_ALIASES.items():
        if canonical == clean and raw in data:
            return data.get(raw)
    return data.get(clean)


def ordered_proposed_items(row: dict[str, Any]) -> list[dict[str, Any]]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    fields = proposed_fields(payload)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(key: Any, value: Any, label: str = "") -> None:
        clean = canonical_field(key)
        if clean in seen or not has_visible_value(value):
            return
        seen.add(clean)
        items.append({"key": clean, "label": label or field_label(clean), "value": value})

    for key in FIELD_ORDER:
        if key in fields:
            add(key, fields[key])
        for raw, canonical in FIELD_ALIASES.items():
            if canonical == key and raw in fields:
                add(raw, fields[raw])
    for key, value in fields.items():
        add(key, value)

    review_type = str(row.get("review_type") or "")
    candidate = candidate_from_payload(payload)
    if not items and review_type == "candidate_clinic":
        for key in ("display_name", "website", "city", "country", "services", "profesionales"):
            if key == "display_name":
                value = candidate.get("name") or candidate.get("clinic_name") or candidate.get("display_name")
            elif key == "profesionales":
                value = candidate.get("profesionales") or candidate.get("professionals")
            else:
                value = candidate.get(key)
            add(key, value)
    if not items and review_type == "source_change_detected":
        hints = payload.get("material_hints")
        if isinstance(hints, list):
            for index, value in enumerate(hints):
                add(f"source_change_{index}", value, "Cambio posible")
    if not items and review_type == "clinic_quality_audit":
        issues = payload.get("issues")
        if isinstance(issues, list):
            for index, issue in enumerate(issues):
                label = issue.get("label") if isinstance(issue, dict) else ""
                add(f"quality_issue_{index}", label or issue, "Campo pendiente")
    if not items and review_type == "clinic_claim_request":
        claim_parts = [
            payload.get("clinic_name") or candidate.get("clinic_name") or candidate.get("name") or row.get("title"),
            payload.get("requester_name"),
            payload.get("requester_email") or payload.get("email"),
            payload.get("message"),
        ]
        add("claim_request", "\n".join(str(part) for part in claim_parts if str(part or "").strip()), "Solicitud de ficha")
    return items


def manual_review_targets(row: dict[str, Any], item: dict[str, Any]) -> list[dict[str, str]]:
    if row.get("review_type") != "clinic_quality_audit":
        return []
    if not str(item.get("key") or "").startswith("quality_issue"):
        return []
    search_value = " ".join(
        str(part)
        for part in [
            item.get("key"),
            item.get("label"),
            *nested_text_values(item.get("value")),
        ]
        if str(part or "").strip()
    )
    return manual_review_targets_for_text(search_value)


def dedupe_targets(targets: list[dict[str, str]]) -> list[dict[str, str]]:
    clean: list[dict[str, str]] = []
    seen: set[str] = set()
    for target in targets:
        key = str(target.get("key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        clean.append(target)
    return clean


def manual_review_context(
    row: dict[str, Any],
    proposed_items: list[dict[str, Any]],
    packet_manual_targets: list[dict[str, str]],
) -> dict[str, Any]:
    if row.get("review_type") != "clinic_quality_audit" or not packet_manual_targets:
        return {}
    issues: list[dict[str, str]] = []
    for item in proposed_items:
        targets = manual_review_targets(row, item)
        if not targets:
            continue
        issue_label = redacted_text(item.get("value"), include_values=False) or str(item.get("label") or "").strip()
        for target in targets:
            issues.append({
                "issue_label": issue_label,
                "target_key": target["key"],
                "target_label": target["label"],
                "admin_target_id": target["admin_target_id"],
            })
    return {
        "mode": "manual_admin_field_review",
        "display_title": review_display_title(row),
        "primary_target": packet_manual_targets[0],
        "issues": issues,
        "operator_action": "open_admin_target_edit_field_then_save_clinic",
        "after_save": "resolve_current_review_then_advance_to_next_pending",
        "source_handoff": {
            "available": True,
            "ui_label": "Pasar URL al agente",
            "source_requirement": "official_clinic_url",
            "target_scope": "primary_target_first",
            "allowed_output": "review_queue_proposal_only",
        },
        "llm_boundary": "do_not_invent_values_or_write_field_changes",
    }


def source_candidates(payload: dict[str, Any]) -> list[tuple[str, str]]:
    candidate = candidate_from_payload(payload)
    values: list[tuple[str, str]] = []

    def add(label: str, value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                add(label, item)
            return
        clean = str(value or "").strip()
        if not clean or any(existing == clean for _, existing in values):
            return
        values.append((label, clean))

    add("Fuente", payload.get("source_url"))
    add("Fuente", payload.get("source_urls"))
    add("Fuente", payload.get("sources"))
    add("Fuente", payload.get("candidate_source_url"))
    add("Fuente", candidate.get("source_url"))
    add("Fuente", candidate.get("source_urls"))
    add("Fuente", candidate.get("sources"))
    add("Web propuesta", candidate.get("website") or candidate.get("web") or payload.get("website"))
    for key, label in [
        ("maps_url", "Google Maps propuesto"),
        ("google_maps_url", "Google Maps propuesto"),
        ("google_reviews_url", "Valoraciones propuestas"),
        ("reviews_url", "Valoraciones propuestas"),
        ("pricing_url", "Fuente de precios"),
    ]:
        add(label, proposed_fields(payload).get(key))
    return values


def specialist_source_urls(payload: dict[str, Any]) -> list[str]:
    candidate = candidate_from_payload(payload)
    urls: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                add(item)
            return
        clean = str(value or "").strip()
        if clean and clean not in urls:
            urls.append(clean)

    add(payload.get("source_url"))
    add(payload.get("source_urls"))
    add(payload.get("sources"))
    add(payload.get("candidate_source_url"))
    add(payload.get("website"))
    add(candidate.get("source_url"))
    add(candidate.get("source_urls"))
    add(candidate.get("sources"))
    add(candidate.get("website") or candidate.get("web"))
    return urls


def has_specialist_proposal_without_source(row: dict[str, Any], payload: dict[str, Any]) -> bool:
    if row.get("review_type") != "clinic_profile_enrichment":
        return False
    fields = proposed_fields(payload)
    professionals = fields.get("profesionales") or fields.get("professionals")
    return count_visible_items(professionals) > 0 and not specialist_source_urls(payload)


def specialist_source_job_request(row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if not has_specialist_proposal_without_source(row, payload):
        return {}
    return {
        "job_type": "EXTRACT_CLINIC_PROFILE",
        "status": "operator_supplied_source_required",
        "from_review_id": row.get("id"),
        "requested_fields": ["profesionales"],
        "requested_field_labels": ["Especialistas publicados"],
        "primary_requested_fields": ["profesionales"],
        "primary_requested_field_labels": ["Especialistas publicados"],
        "source_requirement": "official_clinic_team_or_specialist_url",
        "ui_route": "review_card_specialist_source_handoff",
        "target_scope": "specialist_source_only",
        "write_policy": "creates_review_proposal_only",
        "allowed_output": "review_queue_proposal_only",
    }


def evidence_packet(label: str, value: str, include_values: bool) -> dict[str, Any]:
    parsed = urlparse(value)
    packet = {
        "label": label,
        "kind": "url" if parsed.scheme and parsed.netloc else "text",
    }
    if parsed.netloc:
        packet["host"] = parsed.netloc
    if include_values:
        packet["value"] = value
    return packet


def source_job_context(payload: dict[str, Any], include_values: bool = False) -> dict[str, Any]:
    if not (
        payload.get("human_supplied_source")
        or payload.get("from_review_id")
        or payload.get("target_scope")
        or payload.get("ui_route")
    ):
        return {}
    source_url = str(payload.get("source_url") or "").strip()
    source_host = urlparse(source_url).netloc if source_url else ""
    context = {
        "mode": "operator_supplied_source_review",
        "from_review_id": payload.get("from_review_id"),
        "human_supplied_source": bool(payload.get("human_supplied_source")),
        "requested_fields": clean_list(payload.get("requested_fields")),
        "requested_field_labels": clean_list(payload.get("requested_field_labels")),
        "primary_requested_fields": clean_list(payload.get("primary_requested_fields")),
        "primary_requested_field_labels": clean_list(payload.get("primary_requested_field_labels")),
        "operator_requested_field_keys": clean_list(payload.get("operator_requested_field_keys")),
        "operator_requested_field_labels": clean_list(payload.get("operator_requested_field_labels")),
        "operator_requested_field_summary": str(payload.get("operator_requested_field_summary") or "").strip(),
        "target_scope": str(payload.get("target_scope") or "").strip(),
        "ui_route": str(payload.get("ui_route") or "").strip(),
        "allowed_output": str(payload.get("allowed_output") or "review_queue_proposal_only").strip(),
        "write_policy": "creates_review_proposal_only",
        "llm_boundary": str(payload.get("llm_boundary") or "respect_source_job_context_scope").strip(),
        "operator_intent": redacted_text(payload.get("operator_intent"), include_values),
    }
    if source_host:
        context["source_host"] = source_host
    if include_values and source_url:
        context["source_url"] = source_url
    return {key: value for key, value in context.items() if has_visible_value(value)}


def source_origin_status(payload: dict[str, Any], include_values: bool = False) -> dict[str, Any]:
    context = source_job_context(payload, include_values=include_values)
    sources = source_candidates(payload)
    first_source = sources[0][1] if sources else ""
    host = urlparse(first_source).netloc if first_source else ""
    if context:
        status = {
            "status": "context_ready",
            "llm_boundary": "respect_source_job_context_scope",
        }
    elif sources:
        status = {
            "status": "source_without_context",
            "next_step": "review_manually_do_not_infer_original_intent_from_url",
            "llm_boundary": "do_not_infer_operator_intent_from_source_host_only",
        }
    else:
        return {}
    if host:
        status["source_host"] = host
    if include_values and first_source:
        status["source_url"] = first_source
    return status


def google_maps_urls_from_value(key: str, value: Any) -> list[str]:
    clean_key = canonical_field(key)
    if clean_key == "maps_url":
        return [str(item).strip() for item in field_values(value) if str(item or "").strip()]
    if clean_key != "locations":
        return []
    locations = value if isinstance(value, list) else [value]
    urls: list[str] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        for map_key in ("maps_url", "google_maps_url", "map_url"):
            clean = str(location.get(map_key) or "").strip()
            if clean:
                urls.append(clean)
    return urls


def google_maps_review_context(key: str, value: Any) -> dict[str, Any]:
    urls = google_maps_urls_from_value(key, value)
    if not urls:
        return {}
    counts: dict[str, int] = {}
    for url in urls:
        status = google_maps_review_status(url)
        counts[status] = counts.get(status, 0) + 1
    has_direct = counts.get("direct_profile", 0) > 0
    has_unsafe = any(counts.get(status, 0) > 0 for status in ("search_or_route", "street_address", "needs_manual_review", "not_google_maps"))
    if has_unsafe:
        overall = "needs_correction_before_approval"
        label = "No guardar tal cual"
        next_step = "reject_or_modify_with_real_clinic_google_business_profile"
    elif has_direct:
        overall = "direct_profile_needs_human_confirmation"
        label = GOOGLE_MAPS_STATUS_LABELS["direct_profile"]
        next_step = "open_link_and_confirm_same_clinic_before_approval"
    else:
        overall = "no_usable_maps_link"
        label = "Sin perfil de Google Maps útil"
        next_step = "keep_google_maps_pending"
    return {
        "kind": "google_maps_profile_link",
        "overall_status": overall,
        "status_counts": counts,
        "human_label": label,
        "required_human_check": "confirm_real_clinic_google_business_profile",
        "next_step": next_step,
        "safe_to_auto_publish": False,
    }


def google_maps_profile_dependency(clinic: dict[str, Any], fields: dict[str, Any]) -> dict[str, Any]:
    data = clinic.get("current_data") if isinstance(clinic.get("current_data"), dict) else {}
    current_urls = [
        str(data.get(key) or "").strip()
        for key in ("maps_url", "google_maps_url", "map_url")
        if str(data.get(key) or "").strip()
    ]
    current_urls.extend(google_maps_urls_from_value("locations", data.get("locations")))
    proposed_urls: list[str] = []
    for key, value in fields.items():
        if canonical_field(key) in {"maps_url", "locations"}:
            proposed_urls.extend(google_maps_urls_from_value(key, value))
    current_direct = any(google_maps_review_status(url) == "direct_profile" for url in current_urls)
    proposed_direct = any(google_maps_review_status(url) == "direct_profile" for url in proposed_urls)
    source = "current_clinic_profile" if current_direct else "same_review_packet" if proposed_direct else "missing"
    return {
        "field": "maps_url",
        "required_before_approval": True,
        "satisfied": current_direct or proposed_direct,
        "source": source,
        "current_profile_present": current_direct,
        "same_packet_profile_proposed": proposed_direct,
    }


def google_reviews_review_context(
    key: str,
    value: Any,
    clinic: dict[str, Any] | None = None,
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if canonical_field(key) != "google_reviews_url":
        return {}
    urls = [str(item).strip() for item in field_values(value) if str(item or "").strip()]
    if not urls:
        return {}
    dependency = google_maps_profile_dependency(clinic or {}, fields or {})
    return {
        "kind": "google_reviews_link",
        "overall_status": "reviews_link_needs_main_profile_confirmation",
        "url_count": len(urls),
        "human_label": "Confirmar misma ficha",
        "approval_dependency": dependency,
        "required_human_check": "confirm_reviews_match_main_google_business_profile",
        "next_step": "confirm_reviews_match_confirmed_google_maps_profile"
        if dependency["satisfied"]
        else "confirm_main_google_maps_profile_before_approval",
        "safe_to_auto_publish": False,
    }


def phone_warning(key: str, value: Any) -> str:
    if canonical_field(key) not in PHONE_FIELDS:
        return ""
    digits = {normalized_phone_digits(str(item)) for item in field_values(value)}
    digits = {item for item in digits if item}
    if not digits:
        return ""
    if any(len(item) != 9 or item[0] not in {"6", "7", "8", "9"} for item in digits):
        return "Teléfono dudoso: corrige o rechaza antes de aprobar."
    return ""


def maps_warning(key: str, value: Any) -> str:
    if canonical_field(key) != "maps_url":
        return ""
    for item in field_values(value):
        status = google_maps_review_status(item)
        if status in {"search_or_route", "street_address", "needs_manual_review"}:
            return "Google Maps debe ser el perfil real de la clínica, no una búsqueda, ruta o dirección."
    return ""


def warning_items(row: dict[str, Any], proposed_items: list[dict[str, Any]], include_values: bool = False) -> list[str]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    fields = proposed_fields(payload)
    clinic = row.get("clinic") if isinstance(row.get("clinic"), dict) else {}
    warnings: list[str] = []

    def add(value: Any) -> None:
        clean = redacted_text(value, include_values)
        if clean and clean not in warnings:
            warnings.append(clean)

    if row.get("review_type") == "clinic_claim_request":
        add("Reclamación de ficha: no confirma identidad, no concede acceso y no cambia datos por sí sola.")
    if row.get("review_type") == "clinic_quality_audit" and payload.get("quality_context") == "blocking_claims":
        add("Claim bloqueante: compara la evidencia antes de aprobar datos públicos.")
    if as_float(payload.get("duplicate_probability")) >= 0.9:
        add("Duplicado probable: no crear una ficha nueva sin revisión humana.")
    payload_warnings = payload.get("warnings")
    if isinstance(payload_warnings, list):
        for warning in payload_warnings:
            add(warning)
    for item in proposed_items:
        key = item["key"]
        value = item["value"]
        add(phone_warning(key, value))
        add(maps_warning(key, value))
        if key == "locations":
            for location in value if isinstance(value, list) else []:
                if isinstance(location, dict):
                    add(maps_warning("maps_url", location.get("maps_url") or location.get("google_maps_url")))
        if key == "google_reviews_url":
            dependency = google_maps_profile_dependency(clinic if isinstance(clinic, dict) else {}, fields)
            if not dependency["satisfied"]:
                add("Valoraciones Google requiere confirmar primero el perfil real de Google Maps de la clínica.")
        if key in {"status", "profile_confidence", "verification_status"}:
            add(f"{field_label(key)} no se cambia desde aprobación directa.")
        if key in SENSITIVE_FIELDS:
            add(f"{field_label(key)} requiere revisión humana antes de uso público.")
    return warnings


def clinic_identity(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    candidate = candidate_from_payload(payload)
    clinic = row.get("clinic") if isinstance(row.get("clinic"), dict) else {}
    name = (
        clinic.get("display_name")
        or candidate.get("name")
        or candidate.get("clinic_name")
        or payload.get("clinic_name")
        or row.get("clinic_name")
        or row.get("title")
        or "Clínica sin nombre"
    )
    city = clinic.get("city") or candidate.get("city") or payload.get("city") or row.get("city")
    country = clinic.get("country") or candidate.get("country") or payload.get("country")
    return {
        "id": clinic.get("id") or row.get("clinic_id"),
        "name": name,
        "slug": clinic.get("slug") or row.get("clinic_slug"),
        "city": city,
        "country": country,
        "status": clinic.get("status") or row.get("clinic_status") or ("candidate" if row.get("review_type") == "candidate_clinic" else None),
    }


def decision_packet(row: dict[str, Any], include_values: bool = False) -> dict[str, Any]:
    clinic = row.get("clinic") if isinstance(row.get("clinic"), dict) else {}
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    fields = proposed_fields(payload)
    proposed_items = ordered_proposed_items(row)
    proposal_fields = []
    all_manual_targets: list[dict[str, str]] = []
    for item in proposed_items:
        key = item["key"]
        field_packet = {
            "key": key,
            "label": item["label"],
            "synthetic": is_synthetic_field(key),
            "current": value_packet(None if is_synthetic_field(key) else current_field_value(clinic, key), include_values),
            "proposed": value_packet(item["value"], include_values),
        }
        maps_context = google_maps_review_context(key, item["value"])
        if maps_context:
            field_packet["google_maps_review"] = maps_context
        reviews_context = google_reviews_review_context(key, item["value"], clinic=clinic, fields=fields)
        if reviews_context:
            field_packet["google_reviews_review"] = reviews_context
        targets = manual_review_targets(row, item)
        if targets:
            field_packet["manual_review_targets"] = targets
            field_packet["manual_review_target"] = targets[0]
            all_manual_targets.extend(targets)
        proposal_fields.append(field_packet)
    evidence = [evidence_packet(label, value, include_values) for label, value in source_candidates(payload)]
    warnings = warning_items(row, proposed_items, include_values=include_values)
    editable_fields = [
        {"key": item["key"], "label": item["label"]}
        for item in proposal_fields
        if not item["synthetic"]
    ]
    packet = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "review_id": row.get("id"),
        "title": row.get("title"),
        "display_title": review_display_title(row),
        "decision_scope": "single_review_item",
        "review_type": row.get("review_type"),
        "proposal_type": review_type_label(row.get("review_type")),
        "priority": row.get("priority"),
        "created_at": row.get("created_at"),
        "clinic": clinic_identity(row),
        "current_relevant": [item for item in proposal_fields if not item["synthetic"]],
        "proposed_change": proposal_fields,
        "evidence": evidence,
        "warnings": warnings,
        "allowed_actions": DECISION_ACTIONS,
        "editable_fields": editable_fields,
        "automation_contract": {
            "llm_role": "prepare_suggestions_only",
            "human_gate": "Daniel must choose approve, reject or modify in the review card.",
            "write_policy": "read_only_packet",
            "scope": "single_review_item",
            "after_decision": "resolve_current_review_then_advance_to_next_pending",
        },
    }
    operator_source_context = source_job_context(payload, include_values=include_values)
    if operator_source_context:
        packet["source_job_context"] = operator_source_context
    origin_status = source_origin_status(payload, include_values=include_values)
    if origin_status:
        packet["source_origin_status"] = origin_status
    packet_manual_targets = dedupe_targets(all_manual_targets)
    if packet_manual_targets:
        packet["manual_review_targets"] = packet_manual_targets
        packet["manual_review_context"] = manual_review_context(row, proposed_items, packet_manual_targets)
        packet["source_job_request"] = {
            "job_type": "EXTRACT_CLINIC_PROFILE",
            "status": "operator_supplied_source_required",
            "from_review_id": row.get("id"),
            "requested_fields": [target["key"] for target in packet_manual_targets],
            "requested_field_labels": [target["label"] for target in packet_manual_targets],
            "primary_requested_fields": [packet_manual_targets[0]["key"]],
            "primary_requested_field_labels": [packet_manual_targets[0]["label"]],
            "source_requirement": "official_clinic_url",
            "ui_route": "manual_review_banner_source_handoff",
            "target_scope": "primary_target_first",
            "write_policy": "creates_review_proposal_only",
            "allowed_output": "review_queue_proposal_only",
        }
    specialist_source_request = specialist_source_job_request(row, payload)
    if specialist_source_request and "source_job_request" not in packet:
        packet["source_job_request"] = specialist_source_request
    if not include_values:
        packet["safe_default"] = True
    return packet


def packet_has_manual_target_prompt_route(packet: dict[str, Any]) -> bool:
    return bool(
        packet.get("review_type") == "clinic_quality_audit"
        and packet.get("manual_review_targets")
        and packet.get("manual_review_context")
    )


def packet_llm_readiness_status(packet: dict[str, Any]) -> str:
    if packet_has_manual_target_prompt_route(packet):
        return "manual_target_prompt_ready"
    source_origin = packet.get("source_origin_status")
    if isinstance(source_origin, dict) and source_origin.get("status") == "source_without_context":
        return "blocked_source_without_context"
    return "strict_prompt_ready"


def packet_is_llm_ready(packet: dict[str, Any]) -> bool:
    return packet_llm_readiness_status(packet) != "blocked_source_without_context"


def build_report(
    rows: list[dict[str, Any]],
    include_values: bool = False,
    llm_ready_only: bool = False,
) -> dict[str, Any]:
    packets = [decision_packet(row, include_values=include_values) for row in rows if isinstance(row, dict)]
    excluded_source_without_context = 0
    if llm_ready_only:
        filtered_packets = []
        for packet in packets:
            if packet_is_llm_ready(packet):
                filtered_packets.append(packet)
            else:
                excluded_source_without_context += 1
        packets = filtered_packets
    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "writes_data": False,
        "include_values": include_values,
        "llm_ready_only": llm_ready_only,
        "excluded_source_without_context": excluded_source_without_context,
        "decision_scope": "one_card_one_decision",
        "packet_count": len(packets),
        "packets": packets,
    }


def load_rows(limit: int, local_env: dict[str, str], clinic: str = "", review_id: str = "") -> list[dict[str, Any]]:
    filters = ["rq.status = 'open'"]
    if review_id:
        filters.append(f"rq.id = {sql_literal(review_id)}::uuid")
    clean_clinic = clinic.strip()
    if clean_clinic:
        like_literal = sql_literal(f"%{clean_clinic}%")
        compact_literal = sql_literal(f"%{compact_lookup_key(clean_clinic)}%")
        filters.append(f"""
        (
          rq.title ilike {like_literal}
          or c.slug ilike {like_literal}
          or c.display_name ilike {like_literal}
          or regexp_replace(translate(lower(coalesce(c.slug, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact_literal}
          or regexp_replace(translate(lower(coalesce(c.display_name, '')), 'áéíóúüñ', 'aeiouun'), '[^a-z0-9]+', '', 'g') like {compact_literal}
        )
""")
    where_sql = "\n    and ".join(filters)
    capped_limit = max(1, min(50, int(limit)))
    sql = f"""
with review_rows as (
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
    c.country,
    c.status as clinic_status,
    case
      when c.id is null then null
      else jsonb_build_object(
        'id', c.id,
        'slug', c.slug,
        'display_name', c.display_name,
        'website', c.website,
        'country', c.country,
        'city', c.city,
        'region', c.region,
        'address', c.address,
        'status', c.status,
        'summary', c.summary,
        'profile_confidence', c.profile_confidence,
        'verification_status', c.verification_status,
        'current_data', c.current_data
      )
    end as clinic
  from public.review_queue rq
  left join public.clinics c on c.id = rq.clinic_id
  where {where_sql}
  order by rq.priority desc, rq.created_at asc, rq.title asc, rq.id asc
  limit {capped_limit}
)
select coalesce(jsonb_agg(to_jsonb(review_rows) order by priority desc, created_at asc, title asc, id asc), '[]'::jsonb)
from review_rows;
"""
    return json.loads(run_psql(sql, local_env))


def load_input_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("reviews", "open_reviews", "items", "rows"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
    raise SystemExit("Input file must contain a review list.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--clinic", default="", help="Clinic name, slug or review-title fragment.")
    parser.add_argument("--review-id", default="", help="Open review_queue id.")
    parser.add_argument("--input-file", type=Path, help="Read review rows from a local JSON file instead of Supabase.")
    parser.add_argument("--llm-ready-only", action="store_true", help="Exclude source-only cards that lack operator/job context.")
    parser.add_argument("--include-values", action="store_true", help="Include proposed/current values and full evidence URLs for local LLM preparation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input_file:
        rows = load_input_file(args.input_file)
    else:
        rows = load_rows(args.limit, load_env_file(), clinic=args.clinic, review_id=args.review_id)
    print(json.dumps(
        build_report(rows, include_values=args.include_values, llm_ready_only=args.llm_ready_only),
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
