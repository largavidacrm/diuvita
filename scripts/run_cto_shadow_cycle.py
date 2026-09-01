#!/usr/bin/env python3
"""Run the safe Vitalarga CTO shadow cycle.

This orchestrates idempotent internal tools. It avoids public profile edits,
candidate draft promotion and auto-publication.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from admin_digest import (
    SAFE_WRITE_REVIEW_BACKLOG_LIMIT,
    as_int,
    google_link_review_status,
    next_action_label,
    next_source_action,
    review_backlog_guard_status,
    source_coverage_status,
    specialist_review_status,
    top_pending_profile_field,
)
from daniel_review_brief import priority_review_click, profile_queue_signal


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DEFAULT_SAFE_WRITE_REVIEW_BACKLOG_STOP = max(1, SAFE_WRITE_REVIEW_BACKLOG_LIMIT - 5)


def try_parse_json(output: str) -> Any:
    text = output.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


STEP_ITEM_KEYS = {
    "capture_enrichment_review_claims": (
        "title",
        "review_id",
        "field_claims_created",
        "source_records_created",
    ),
    "seed_visible_clinic_sources": (
        "clinic_name",
        "city",
        "status",
        "website",
        "source_url",
        "source_type",
    ),
    "discover_clinic_team_sources": (
        "clinic_slug",
        "clinic_name",
        "city",
        "status",
        "url",
        "label",
        "score",
        "already_stored",
        "source_type",
    ),
    "discover_clinic_google_links": (
        "clinic_slug",
        "clinic_name",
        "website",
        "status",
        "proposed_fields",
        "created_review",
    ),
    "hydrate_source_records": ("source_url", "status"),
    "monitor_source_changes": ("source_url", "clinic_name", "status", "hash"),
    "process_source_change_reviews": (
        "clinic_slug",
        "source_url",
        "status",
        "proposed_fields",
        "created_review",
    ),
    "submit_blocking_claim_reviews": ("clinic_slug", "clinic_name", "status", "claims"),
    "measure_source_snapshot_retention": ("clinic_name", "source_url", "snapshots", "prunable"),
    "measure_source_coverage": (
        "clinic_name",
        "slug",
        "status",
        "source_records",
        "hydrated_source_records",
        "total_claims",
        "claims_without_source",
        "blocking_claims",
    ),
    "measure_profile_completeness": (
        "clinic_name",
        "slug",
        "status",
        "pending_count",
        "pending_fields",
        "open_quality_reviews",
    ),
    "clinic_publication_readiness": (
        "slug",
        "clinic_name",
        "city",
        "status",
        "open_reviews",
        "open_blocking_reviews",
    ),
    "review_backlog_brief": (
        "clinic_name",
        "clinic_slug",
        "city",
        "clinic_status",
        "card_count",
        "blocking_claim_reviews",
        "enrichment_reviews",
        "source_change_reviews",
        "quality_reviews",
        "candidate_reviews",
        "max_priority",
        "oldest_created_at",
    ),
    "manual_review_route_brief": (
        "title",
        "clinic_name",
        "review_type",
        "proposal_type",
        "priority",
        "operator_action",
        "human_next_step",
        "llm_help_scope",
        "manual_primary_target",
        "manual_target_labels",
        "source_origin_status",
        "source_handoff",
        "editable_field_count",
        "proposed_field_count",
        "warning_count",
        "writes_data",
        "calls_llm",
    ),
    "consolidate_profile_enrichment_reviews": (
        "clinic_name",
        "clinic_slug",
        "city",
        "clinic_status",
        "card_count",
        "source_count",
        "merged_field_count",
        "merged_field_counts",
        "already_present_count",
        "conflict_count",
        "conflict_fields",
        "weak_phone_count",
        "weak_phone_fields",
        "next_step",
    ),
    "admin_digest": ("title", "review_type", "priority", "clinic_name", "clinic_slug", "professionals_count"),
    "submit_source_shadow_reviews": (
        "clinic_slug",
        "clinic_name",
        "source_url",
        "status",
        "pending_count",
        "pending_fields",
        "proposed_fields",
        "created_review",
    ),
    "process_extract_clinic_profile_jobs": (
        "job_id",
        "clinic_slug",
        "clinic_name",
        "source_url",
        "status",
        "requested_fields",
        "missing_fields",
        "proposed_fields",
        "created_review",
    ),
    "process_discovery_recommendation_jobs": (
        "job_id",
        "status",
        "source_url",
        "candidate",
        "completed_job",
        "reason",
    ),
    "check_production_health": ("name", "url", "status", "ok", "missing_markers", "error"),
    "check_public_site_freshness": ("slug", "name", "url", "fresh", "missing_markers", "error"),
    "clinic_public_visibility_report": ("slug", "clinic_name", "status", "updated_at"),
    "google_link_review_reconciliation": (
        "clinic_name",
        "clinic_slug",
        "title",
        "priority",
        "direct_map_count",
        "unsafe_map_count",
        "review_link_count",
        "map_status_counts",
        "next_step",
    ),
    "specialist_review_reconciliation": (
        "clinic_name",
        "slug",
        "city",
        "status",
        "published_count",
        "review_card_count",
        "review_professional_count",
        "claim_professional_count",
        "pending_professional_count",
        "next_step",
    ),
    "export_specialist_claim_proposals": (
        "slug",
        "title",
        "priority",
        "source_url",
        "source_urls",
    ),
}


STEP_LABELS = {
    "capture_enrichment_review_claims": "captura de claims desde propuestas",
    "seed_visible_clinic_sources": "siembra de webs oficiales como fuentes",
    "discover_clinic_team_sources": "descubrimiento de paginas de equipo",
    "discover_clinic_google_links": "descubrimiento de Google Maps y valoraciones",
    "hydrate_source_records": "hidratacion de fuentes",
    "monitor_source_changes": "vigilancia de cambios de fuentes",
    "process_source_change_reviews": "conversion de cambios en propuestas",
    "submit_source_shadow_reviews": "extraccion shadow desde fuentes guardadas",
    "process_extract_clinic_profile_jobs": "extraccion desde fuentes indicadas en revision",
    "process_discovery_recommendation_jobs": "recomendaciones con link oficial",
    "submit_blocking_claim_reviews": "claims bloqueantes",
    "measure_source_snapshot_retention": "retencion de evidencias",
    "measure_source_coverage": "cobertura de fuentes",
    "measure_profile_completeness": "completitud de fichas",
    "clinic_publication_readiness": "preparacion para publicacion",
    "review_backlog_brief": "atascos de bandeja",
    "manual_review_route_brief": "rutas de revision manual",
    "consolidate_profile_enrichment_reviews": "consolidacion de mejoras duplicadas",
    "admin_digest": "resumen interno",
    "evaluate_claim_rules": "reglas de publicacion",
    "check_operational_limits_strict": "limites operativos",
    "check_production_health": "salud de la web publica",
    "check_public_site_freshness": "frescura de la web publica",
    "clinic_public_visibility_report": "visibilidad publica por clinica",
    "google_link_review_reconciliation": "conciliacion de enlaces Google",
    "specialist_review_reconciliation": "conciliacion de especialistas",
    "export_specialist_claim_proposals": "propuestas privadas de especialistas",
}

REVIEW_CARD_CREATING_STEPS = {
    "monitor_source_changes",
    "process_source_change_reviews",
    "discover_clinic_google_links",
    "submit_source_shadow_reviews",
    "process_extract_clinic_profile_jobs",
    "process_discovery_recommendation_jobs",
    "submit_blocking_claim_reviews",
}


def compact_item(item: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(item, dict) or not keys:
        return item
    return {key: item[key] for key in keys if key in item}


def compact_summary(name: str, summary: Any) -> Any:
    if not isinstance(summary, dict):
        return summary
    compact = dict(summary)
    compact.pop("admin_email", None)
    if name == "clinic_public_visibility_report":
        readiness = compact.get("readiness")
        if isinstance(readiness, dict):
            matches = [item for item in readiness.get("matches") or [] if isinstance(item, dict)]
            compact["readiness"] = {
                "query": readiness.get("query"),
                "matches_count": len(matches),
                "sample_matches": [
                    compact_item(item, STEP_ITEM_KEYS.get(name, ()))
                    for item in matches[:3]
                ],
            }
        freshness = compact.get("freshness")
        if isinstance(freshness, dict):
            checks = [item for item in freshness.get("checks") or [] if isinstance(item, dict)]
            compact["freshness"] = {
                "ok": freshness.get("ok"),
                "clinic_count": freshness.get("clinic_count"),
                "stale_count": freshness.get("stale_count"),
                "sample_checks": [
                    compact_item(item, STEP_ITEM_KEYS.get("check_public_site_freshness", ()))
                    for item in checks[:3]
                ],
            }
    items = compact.get("items")
    if isinstance(items, list):
        compact["items_count"] = len(items)
        compact["sample_items"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in items[:3]
        ]
        compact.pop("items", None)
    evaluations = compact.get("evaluations")
    if isinstance(evaluations, list):
        compact["evaluations_count"] = len(evaluations)
        compact.pop("evaluations", None)
    top_sources = compact.get("top_sources")
    if isinstance(top_sources, list):
        compact["top_sources_count"] = len(top_sources)
        compact["sample_top_sources"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in top_sources[:3]
        ]
        compact.pop("top_sources", None)
    pending_profiles = compact.get("pending_profiles")
    if isinstance(pending_profiles, list):
        compact["pending_profiles_count"] = len(pending_profiles)
        compact["sample_pending_profiles"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in pending_profiles[:3]
        ]
        compact.pop("pending_profiles", None)
    source_work = compact.get("needs_source_work")
    if isinstance(source_work, list):
        compact["needs_source_work_count"] = len(source_work)
        compact["sample_needs_source_work"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in source_work[:3]
        ]
        compact.pop("needs_source_work", None)
    duplicate_enrichment = compact.get("duplicate_enrichment")
    if isinstance(duplicate_enrichment, list):
        compact["duplicate_enrichment_count"] = len(duplicate_enrichment)
        compact["sample_duplicate_enrichment"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in duplicate_enrichment[:3]
        ]
        compact.pop("duplicate_enrichment", None)
    clinic_workgroups = compact.get("clinic_workgroups")
    if isinstance(clinic_workgroups, list):
        compact["clinic_workgroups_count"] = len(clinic_workgroups)
        compact["sample_clinic_workgroups"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in clinic_workgroups[:3]
        ]
        compact.pop("clinic_workgroups", None)
    groups = compact.get("groups")
    if isinstance(groups, list):
        compact["groups_count"] = len(groups)
        compact["sample_groups"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in groups[:3]
        ]
        compact.pop("groups", None)
    open_reviews = compact.get("open_reviews")
    if isinstance(open_reviews, list):
        compact["open_reviews_count"] = len(open_reviews)
        compact["sample_open_reviews"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in open_reviews[:3]
        ]
        compact.pop("open_reviews", None)
    backlog_quality = compact.get("review_backlog_quality")
    if isinstance(backlog_quality, dict):
        compact["review_backlog_quality"] = {
            "duplicate_enrichment_clinics": backlog_quality.get("duplicate_enrichment_clinics", 0),
            "duplicate_enrichment_reviews": backlog_quality.get("duplicate_enrichment_reviews", 0),
        }
    review_examples = compact.get("review_examples_by_type")
    if isinstance(review_examples, list):
        compact["review_examples_by_type_count"] = len(review_examples)
        compact["sample_review_examples_by_type"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in review_examples[:5]
        ]
        compact.pop("review_examples_by_type", None)
    review_cards = compact.get("review_cards")
    if isinstance(review_cards, list):
        compact["review_cards_count"] = len(review_cards)
        compact["sample_review_cards"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in review_cards[:3]
        ]
        compact.pop("review_cards", None)
    matches = compact.get("matches")
    if isinstance(matches, list):
        compact["matches_count"] = len(matches)
        compact["sample_matches"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in matches[:3]
        ]
        compact.pop("matches", None)
    proposals = compact.get("proposals")
    if isinstance(proposals, list):
        compact["proposals_count"] = len(proposals)
        compact["sample_proposals"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in proposals[:3]
        ]
        compact.pop("proposals", None)
    checks = compact.get("checks")
    if isinstance(checks, list):
        compact["checks_count"] = len(checks)
        compact["sample_checks"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in checks[:5]
        ]
        compact.pop("checks", None)
    clinics = compact.get("clinics")
    if isinstance(clinics, list):
        compact["clinics_count"] = len(clinics)
        compact["sample_clinics"] = [
            compact_item(item, STEP_ITEM_KEYS.get(name, ()))
            for item in clinics[:3]
        ]
        compact.pop("clinics", None)
    return compact


def run_step(name: str, args: list[str], timeout: int) -> dict[str, Any]:
    started = time.time()
    command = [sys.executable, str(SCRIPTS / args[0]), *args[1:]]
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    duration = round(time.time() - started, 2)
    summary = try_parse_json(result.stdout)
    return {
        "name": name,
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "duration_seconds": duration,
        "summary": compact_summary(name, summary),
        "stdout_tail": ""
        if result.returncode == 0 and summary is not None
        else result.stdout.strip()[-1200:],
        "stderr_tail": result.stderr.strip()[-1200:],
    }


def skipped_step(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": True,
        "skipped": True,
        "returncode": 0,
        "duration_seconds": 0,
        "summary": {"status": "skipped", "reason": reason},
        "stdout_tail": "",
        "stderr_tail": "",
    }


def open_review_count_from_digest(digest: dict[str, Any]) -> int:
    summary = digest.get("summary") if isinstance(digest.get("summary"), dict) else {}
    reviews = summary.get("reviews") if isinstance(summary.get("reviews"), dict) else {}
    return as_int(reviews.get("open"))


def clinic_workgroup_click_from_digest(digest: dict[str, Any]) -> str:
    group = digest.get("review_first_clinic_workgroup") or {}
    name = str(group.get("clinic_name") or group.get("clinic_slug") or "").strip()
    count = as_int(group.get("open_count"))
    if not name or not count:
        return ""
    return f"Filtrar grupo: {name}, {count} tarjetas, una por una."


def cycle_next_clicks(digest: dict[str, Any]) -> list[str]:
    if not digest:
        return ["Abrir el panel y usar Abrir prioridad."]
    clicks: list[str] = []
    guard = review_backlog_guard_status(digest)
    if guard.startswith(("margen corto", "pausa preventiva", "freno activo")):
        clicks.append(f"No crear trabajos nuevos: {guard}.")
    priority_click = priority_review_click(digest)
    if priority_click:
        clicks.append(priority_click)
    specialists = specialist_review_status(digest)
    if not specialists.startswith("sin tarjetas"):
        clicks.append(f"Abrir Especialistas: {specialists}.")
    google_links = google_link_review_status(digest)
    if not google_links.startswith("sin tarjetas"):
        clicks.append(f"Abrir Google Maps: {google_links}.")
    if not clicks:
        workgroup = clinic_workgroup_click_from_digest(digest)
        if workgroup:
            clicks.append(workgroup)
    return clicks[:4] or ["Abrir el panel y usar Abrir prioridad."]


def cycle_profile_queue_signal(digest: dict[str, Any], next_action: str) -> str:
    return profile_queue_signal(digest)


def step_label(name: str) -> str:
    return STEP_LABELS.get(name, name.replace("_", " "))


def first_failed_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if not step.get("ok"):
            return step
    return None


def find_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for step in steps:
        if step.get("name") == name:
            return step
    return None


def safe_step_summary(step: dict[str, Any] | None) -> dict[str, Any]:
    if not step:
        return {}
    summary = step.get("summary")
    return summary if isinstance(summary, dict) else {}


def clinic_visibility_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobada en este ciclo"
    summary = safe_step_summary(step)
    if not step.get("ok"):
        return "revisar"
    readiness = summary.get("readiness") if isinstance(summary.get("readiness"), dict) else {}
    matches = as_int(readiness.get("matches_count"))
    if not matches:
        return "clínica no encontrada"
    freshness = summary.get("freshness") if isinstance(summary.get("freshness"), dict) else {}
    stale = as_int(freshness.get("stale_count"))
    if stale:
        return f"{stale} ficha con desfase"
    if freshness.get("ok") is True:
        return "sin desfase medido"
    if summary.get("freshness_error"):
        return "no se pudo comparar web"
    return "medida"


def publication_readiness_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobada en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    measured = as_int(counts.get("clinics_measured") or summary.get("matches_count"))
    if not measured:
        return "sin fichas medidas"
    ready = as_int(counts.get("ready_clinics"))
    missing = as_int(counts.get("clinics_with_missing_fields"))
    blocking = as_int(counts.get("clinics_with_blocking_reviews"))
    top_missing = counts.get("top_missing_fields") if isinstance(counts.get("top_missing_fields"), list) else []
    top = top_missing[0] if top_missing and isinstance(top_missing[0], dict) else {}
    field = str(top.get("field") or "").strip()
    count = as_int(top.get("count"))
    detail = f"; principal: {field} ({count})" if field and count else ""
    blocking_detail = f"; {blocking} con claims bloqueantes" if blocking else ""
    if missing:
        return f"{ready}/{measured} sin faltantes; {missing} con faltantes{detail}{blocking_detail}"
    return f"{ready}/{measured} sin faltantes obligatorios{blocking_detail}"


def specialist_reconciliation_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobada en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    count = as_int(counts.get("clinics") or summary.get("clinics_count"))
    if not count:
        return "sin fichas medidas"
    pending_total = as_int(counts.get("pending_professionals"))
    cards_total = as_int(counts.get("review_cards"))
    pending_clinics = as_int(counts.get("clinics_with_pending_professionals"))
    if pending_total:
        return f"{pending_total} pendientes en {cards_total} tarjetas ({pending_clinics}/{count} fichas)"
    sample = summary.get("sample_clinics") if isinstance(summary.get("sample_clinics"), list) else []
    first = sample[0] if sample and isinstance(sample[0], dict) else {}
    name = first.get("clinic_name") or first.get("slug") or "primera ficha"
    pending = as_int(first.get("pending_professional_count"))
    cards = as_int(first.get("review_card_count"))
    if pending:
        return f"{name}: {pending} pendientes en {cards} tarjetas"
    return f"{name}: sin pendientes detectados"


def specialist_claim_proposal_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobadas en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    proposals = as_int(counts.get("proposal_count") or summary.get("proposals_count"))
    skipped_cards = as_int(counts.get("skipped_with_open_cards"))
    if proposals:
        return f"{proposals} propuesta privada lista; {skipped_cards} omitidas porque ya tienen tarjeta"
    if skipped_cards:
        return f"sin propuestas nuevas; {skipped_cards} ya tienen tarjeta abierta"
    return "sin propuestas nuevas"


def google_link_reconciliation_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobada en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    cards = as_int(counts.get("review_cards") or summary.get("review_cards_count"))
    if not cards:
        return "sin tarjetas Google medidas"
    direct = as_int(counts.get("cards_with_direct_maps"))
    unsafe = as_int(counts.get("cards_with_unsafe_maps"))
    reviews = as_int(counts.get("cards_with_review_links"))
    if unsafe:
        return f"{unsafe}/{cards} con Maps que no se debe guardar sin corregir"
    if direct:
        return f"{direct}/{cards} con perfil Maps directo; {reviews} con valoraciones"
    return f"{cards} tarjetas sin perfil Maps directo"


def enrichment_consolidation_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobada en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    groups = as_int(counts.get("groups") or summary.get("groups_count"))
    if not groups:
        return "sin mejoras duplicadas"
    cards = as_int(counts.get("cards"))
    conflicts = as_int(counts.get("conflicts"))
    weak_phones = as_int(counts.get("weak_phone_fields"))
    fields = as_int(counts.get("fields_to_review"))
    if conflicts:
        return f"{conflicts} conflictos en {groups} grupos; revisar antes de fusionar"
    if weak_phones:
        return f"{weak_phones} telefonos dudosos en {groups} grupos; revisar antes de fusionar"
    return f"{fields} campos listos para revisar en {groups} grupos ({cards} tarjetas)"


def manual_review_route_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no comprobadas en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    total = as_int(counts.get("reported_packets") or counts.get("total_packets"))
    if not total:
        return "sin tarjetas medidas"
    manual = as_int(counts.get("manual_field_routes"))
    handoff = as_int(counts.get("source_handoff_available"))
    source_only_reviewable = as_int(counts.get("source_only_reviewable"))
    blocked = as_int(counts.get("blocked_without_operator_context"))
    direct = as_int(counts.get("direct_change_reviews"))
    parts: list[str] = []
    if manual:
        parts.append(f"{manual} abren campo directo")
    if handoff:
        parts.append(f"{handoff} permiten URL oficial")
    if source_only_reviewable:
        parts.append(f"{source_only_reviewable} revisables manualmente aunque no listas para LLM")
    if blocked:
        parts.append(f"{blocked} no listas para LLM por fuente sin contexto")
    if direct and not parts:
        parts.append(f"{direct} listas para decision directa")
    return "; ".join(parts) if parts else f"{total} tarjetas sin ruta especial"


def discovery_recommendation_status(step: dict[str, Any] | None) -> str:
    if not step:
        return "no procesadas en este ciclo"
    if not step.get("ok"):
        return "revisar"
    summary = safe_step_summary(step)
    status = str(summary.get("status") or "").strip()
    if status == "empty":
        return "sin recomendaciones con link en cola"
    if status == "needs_search_provider":
        return "pendientes de proveedor de busqueda real"
    if status != "ready":
        return status or "medidas"
    candidate = summary.get("candidate") if isinstance(summary.get("candidate"), dict) else {}
    name = str(candidate.get("name") or candidate.get("website") or "recomendacion").strip()
    counts = candidate.get("field_counts") if isinstance(candidate.get("field_counts"), dict) else {}
    labels = {
        "emails": "emails",
        "locations": "sedes",
        "phones": "telefonos",
        "professionals": "especialistas",
        "services": "servicios",
        "specialties": "especialidades",
        "technologies": "tecnologias",
        "units": "unidades",
    }
    count_text = ", ".join(f"{value} {labels.get(key, key)}" for key, value in sorted(counts.items())[:3])
    completed = summary.get("completed_job") if isinstance(summary.get("completed_job"), dict) else {}
    reviews = as_int(completed.get("review_items_created"))
    if reviews:
        return f"{name}: {reviews} propuesta creada"
    if count_text:
        return f"{name}: lista para crear propuesta ({count_text})"
    return f"{name}: lista para crear propuesta"


def build_cycle_brief(output: dict[str, Any]) -> dict[str, Any]:
    steps = [step for step in output.get("steps") or [] if isinstance(step, dict)]
    failed_step = first_failed_step(steps)
    admin_digest = safe_step_summary(find_step(steps, "admin_digest"))
    admin_summary = admin_digest.get("summary") if isinstance(admin_digest.get("summary"), dict) else {}
    reviews = admin_summary.get("reviews") if isinstance(admin_summary.get("reviews"), dict) else {}
    jobs = admin_summary.get("jobs") if isinstance(admin_summary.get("jobs"), dict) else {}
    automation = admin_summary.get("automation") if isinstance(admin_summary.get("automation"), dict) else {}
    failed_jobs = as_int(jobs.get("failed")) + as_int(jobs.get("dead_letter"))
    open_reviews = as_int(reviews.get("open"))
    mode = str(output.get("mode") or "dry_run")
    mode_label = "solo lectura" if mode == "dry_run" else "cambios internos seguros"
    completed_steps = len([step for step in steps if step.get("ok") and not step.get("skipped")])
    skipped_steps = len([step for step in steps if step.get("skipped")])
    total_steps = len(steps)

    if failed_step:
        failed_name = str(failed_step.get("name") or "")
        if failed_name == "check_operational_limits_strict":
            status = "needs_daniel"
            attention = "Hay una decision de limites operativos para Daniel antes de seguir por esa via."
        elif failed_name == "check_production_health":
            status = "attention"
            attention = "La web publica no paso una comprobacion de salud; conviene revisarla antes de aceptar cambios nuevos."
        elif failed_name == "check_public_site_freshness":
            status = "attention"
            attention = "Hay datos guardados que no parecen estar todavia en la web publica; conviene actualizar la web al final del lote."
        else:
            status = "attention"
            attention = "Hay un fallo tecnico en el ciclo; revisar el paso detenido antes de aceptar nuevas fichas."
        headline = f"Ciclo detenido en {step_label(failed_name)}."
    else:
        if failed_jobs:
            status = "attention"
            attention = "Hay fallos tecnicos abiertos en la bandeja interna."
        elif skipped_steps:
            status = "attention"
            attention = "Se omitieron pasos que podian crear mas tarjetas porque la bandeja ya esta cargada."
        else:
            status = "ok"
            attention = ""
        headline = f"Ciclo completado en modo {mode_label}."

    production_step = find_step(steps, "check_production_health")
    production_summary = safe_step_summary(production_step)
    if not production_step:
        production_health = "no comprobada en este ciclo"
    elif production_step.get("ok") and production_summary.get("ok"):
        production_health = "OK"
    else:
        production_health = "revisar"

    freshness_step = find_step(steps, "check_public_site_freshness")
    freshness_summary = safe_step_summary(freshness_step)
    if not freshness_step:
        public_freshness = "no comprobada en este ciclo"
    elif freshness_step.get("ok") and freshness_summary.get("ok"):
        public_freshness = "OK"
    else:
        stale_count = as_int(freshness_summary.get("stale_count"))
        public_freshness = f"{stale_count} con desfase" if stale_count else "revisar"
    publication_readiness_step = find_step(steps, "clinic_publication_readiness")
    publication_readiness = publication_readiness_status(publication_readiness_step)
    visibility_step = find_step(steps, "clinic_public_visibility_report")
    clinic_visibility = clinic_visibility_status(visibility_step)
    google_link_step = find_step(steps, "google_link_review_reconciliation")
    google_link_reconciliation = google_link_reconciliation_status(google_link_step)
    specialist_step = find_step(steps, "specialist_review_reconciliation")
    specialist_reconciliation = specialist_reconciliation_status(specialist_step)
    specialist_claim_proposal_step = find_step(steps, "export_specialist_claim_proposals")
    specialist_claim_proposals = specialist_claim_proposal_status(specialist_claim_proposal_step)
    enrichment_consolidation_step = find_step(steps, "consolidate_profile_enrichment_reviews")
    enrichment_consolidation = enrichment_consolidation_status(enrichment_consolidation_step)
    manual_route_step = find_step(steps, "manual_review_route_brief")
    manual_review_routes = manual_review_route_status(manual_route_step)
    discovery_recommendation_step = find_step(steps, "process_discovery_recommendation_jobs")
    discovery_recommendations = discovery_recommendation_status(discovery_recommendation_step)

    if admin_digest:
        next_action = next_action_label(admin_digest)
        profile_gap = top_pending_profile_field(admin_digest)
        profile_next = cycle_profile_queue_signal(admin_digest, next_action)
        source_gap = source_coverage_status(admin_digest)
        source_next = next_source_action(admin_digest)
        next_clicks = cycle_next_clicks(admin_digest)
    elif failed_step:
        next_action = "Revisar el paso detenido"
        profile_gap = "no medido"
        profile_next = "no medida"
        source_gap = "no medida"
        source_next = "no medida"
        next_clicks = ["Revisar el paso detenido antes de aceptar nuevas fichas."]
    else:
        next_action = "Sin accion urgente"
        profile_gap = "no medido"
        profile_next = "no medida"
        source_gap = "no medida"
        source_next = "no medida"
        next_clicks = ["Abrir el panel y usar Abrir prioridad."]

    auto_publish = bool(automation.get("auto_publish_enabled"))
    shadow_mode = bool(automation.get("shadow_mode_active"))
    publication_guard = (
        "Auto-publicacion activa; revisar con especial cuidado antes de ampliar reglas."
        if auto_publish
        else "Auto-publicacion apagada; crear borrador no publica."
    )

    return {
        "status": status,
        "headline": headline,
        "mode": mode_label,
        "steps": f"{completed_steps}/{total_steps} pasos OK",
        "skipped_steps": skipped_steps,
        "next_action": next_action,
        "open_reviews": open_reviews,
        "failed_jobs": failed_jobs,
        "profile_gap": profile_gap,
        "profile_next": profile_next,
        "source_gap": source_gap,
        "source_next": source_next,
        "next_clicks": next_clicks,
        "publication_guard": publication_guard,
        "shadow_mode": "activo" if shadow_mode else "inactivo",
        "production_health": production_health,
        "public_freshness": public_freshness,
        "publication_readiness": publication_readiness,
        "clinic_visibility": clinic_visibility,
        "google_link_reconciliation": google_link_reconciliation,
        "specialist_reconciliation": specialist_reconciliation,
        "specialist_claim_proposals": specialist_claim_proposals,
        "enrichment_consolidation": enrichment_consolidation,
        "manual_review_routes": manual_review_routes,
        "discovery_recommendations": discovery_recommendations,
        "attention": attention,
    }


def format_cycle_brief(brief: dict[str, Any]) -> str:
    lines = [
        "# Vitalarga: resumen CTO automatico",
        "",
        f"- Estado: {brief.get('headline')}",
        f"- Pasos: {brief.get('steps')}",
        f"- Que mirar primero: {brief.get('next_action')}.",
        "- Proximos clics: " + " / ".join(str(item) for item in (brief.get("next_clicks") or []) if item),
        f"- Revisiones abiertas: {brief.get('open_reviews')}",
        f"- Campo mas pendiente: {brief.get('profile_gap')}.",
        f"- Fichas pendientes: {brief.get('profile_next')}.",
        f"- Cobertura fuentes: {brief.get('source_gap')}.",
        f"- Siguiente fuente: {brief.get('source_next')}.",
        f"- Publicacion: {brief.get('publication_guard')}",
        f"- Modo sombra: {brief.get('shadow_mode')}.",
        f"- Web publica: {brief.get('production_health')}.",
        f"- Frescura web: {brief.get('public_freshness')}.",
        f"- Preparacion publicacion: {brief.get('publication_readiness')}.",
        f"- Visibilidad clinica: {brief.get('clinic_visibility')}.",
        f"- Consolidacion mejoras: {brief.get('enrichment_consolidation')}.",
        f"- Rutas revision manual: {brief.get('manual_review_routes')}.",
        f"- Recomendaciones con link: {brief.get('discovery_recommendations')}.",
        f"- Conciliacion Google: {brief.get('google_link_reconciliation')}.",
        f"- Conciliacion especialistas: {brief.get('specialist_reconciliation')}.",
        f"- Propuestas especialistas: {brief.get('specialist_claim_proposals')}.",
    ]
    if as_int(brief.get("skipped_steps")):
        lines.append(f"- Pasos omitidos: {brief.get('skipped_steps')}")
    attention = str(brief.get("attention") or "").strip()
    if attention:
        lines.append(f"- Atencion: {attention}")
    return "\n".join(lines) + "\n"


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str], int]]:
    apply_flag = ["--apply"] if args.apply_safe else []
    steps = [
        (
            "capture_enrichment_review_claims",
            ["capture_enrichment_review_claims.py", "--limit", str(args.review_limit), *apply_flag],
            90,
        ),
        (
            "seed_visible_clinic_sources",
            ["seed_visible_clinic_sources.py", "--limit", str(args.seed_source_limit), "--json", *apply_flag],
            45,
        ),
    ]
    if args.team_source_limit:
        team_source_args = [
            "discover_clinic_team_sources.py",
            "--limit",
            str(args.team_source_limit),
            "--timeout",
            str(args.fetch_timeout),
            "--max-links-per-clinic",
            str(args.team_source_max_links),
            *apply_flag,
        ]
        if args.team_source_clinic_slug:
            team_source_args.extend(["--clinic-slug", args.team_source_clinic_slug])
        steps.append(
            (
                "discover_clinic_team_sources",
                team_source_args,
                max(90, args.team_source_limit * args.fetch_timeout + 30),
            )
        )
    if args.google_link_limit:
        google_link_args = [
            "discover_clinic_google_links.py",
            "--limit",
            str(args.google_link_limit),
            "--timeout",
            str(args.fetch_timeout),
            *apply_flag,
        ]
        if args.google_link_clinic_slug:
            google_link_args.extend(["--clinic-slug", args.google_link_clinic_slug])
        if args.google_link_replace_existing:
            google_link_args.append("--replace-existing")
        if args.google_link_allow_multiple_open_clinic_reviews:
            google_link_args.append("--allow-multiple-open-clinic-reviews")
        steps.append(
            (
                "discover_clinic_google_links",
                google_link_args,
                max(90, args.google_link_limit * args.fetch_timeout + 30),
            )
        )
    steps.extend([
        (
            "hydrate_source_records",
            [
                "hydrate_source_records.py",
                "--limit",
                str(args.source_limit),
                "--timeout",
                str(args.fetch_timeout),
                *apply_flag,
            ],
            max(90, args.source_limit * args.fetch_timeout + 30),
        ),
        (
            "monitor_source_changes",
            [
                "monitor_source_changes.py",
                "--limit",
                str(args.monitor_limit),
                "--timeout",
                str(args.fetch_timeout),
                *apply_flag,
            ],
            max(90, args.monitor_limit * args.fetch_timeout + 30),
        ),
        (
            "process_source_change_reviews",
            [
                "process_source_change_reviews.py",
                "--limit",
                str(args.source_change_limit),
                "--timeout",
                str(args.fetch_timeout),
                *apply_flag,
            ],
            max(90, args.source_change_limit * args.fetch_timeout + 30),
        ),
    ])
    if args.extract_profile_job:
        extract_job_args = [
            "process_extract_clinic_profile_jobs.py",
            "--pick-next",
            "--timeout",
            str(args.fetch_timeout),
            "--compact",
            *apply_flag,
        ]
        if args.extract_profile_job_replace_existing:
            extract_job_args.append("--replace-existing")
        if args.extract_profile_job_allow_multiple_open_clinic_reviews:
            extract_job_args.append("--allow-multiple-open-clinic-reviews")
        steps.append(
            (
                "process_extract_clinic_profile_jobs",
                extract_job_args,
                max(90, args.fetch_timeout + 30),
            )
        )
    if args.discovery_recommendation_job:
        steps.append(
            (
                "process_discovery_recommendation_jobs",
                [
                    "process_discovery_recommendation_jobs.py",
                    "--pick-next",
                    "--timeout",
                    str(args.fetch_timeout),
                    "--compact",
                    *apply_flag,
                ],
                max(90, args.fetch_timeout + 30),
            )
        )
    if args.source_shadow_limit:
        source_shadow_args = [
            "submit_source_shadow_reviews.py",
            "--limit",
            str(args.source_shadow_limit),
            "--timeout",
            str(args.fetch_timeout),
            *apply_flag,
        ]
        if args.source_shadow_clinic_slug:
            source_shadow_args.extend(["--clinic-slug", args.source_shadow_clinic_slug])
        if args.source_shadow_replace_existing:
            source_shadow_args.append("--replace-existing")
        steps.append(
            (
                "submit_source_shadow_reviews",
                source_shadow_args,
                max(90, args.source_shadow_limit * args.fetch_timeout + 30),
            )
        )
    steps.extend([
        (
            "submit_blocking_claim_reviews",
            ["submit_blocking_claim_reviews.py", "--limit", str(args.blocking_claim_limit), *apply_flag],
            45,
        ),
        (
            "measure_source_snapshot_retention",
            [
                "measure_source_snapshot_retention.py",
                "--retention-days",
                str(args.snapshot_retention_days),
                "--keep-latest",
                str(args.snapshot_keep_latest),
                "--limit",
                str(args.snapshot_retention_limit),
                "--json",
            ],
            45,
        ),
        (
            "measure_source_coverage",
            ["measure_source_coverage.py", "--limit", str(args.source_coverage_limit), "--json"],
            45,
        ),
        (
            "measure_profile_completeness",
            ["measure_profile_completeness.py", "--limit", str(args.profile_completeness_limit), "--json"],
            45,
        ),
        *(
            [
                (
                    "clinic_publication_readiness",
                    [
                        "clinic_publication_readiness.py",
                        "--limit",
                        str(args.publication_readiness_limit),
                        "--json",
                        *(
                            ["--clinic", args.publication_readiness_clinic]
                            if args.publication_readiness_clinic
                            else []
                        ),
                    ],
                    45,
                )
            ]
            if args.publication_readiness or args.publication_readiness_clinic
            else []
        ),
        (
            "review_backlog_brief",
            ["review_backlog_brief.py", "--limit", str(args.backlog_brief_limit), "--json"],
            45,
        ),
        (
            "manual_review_route_brief",
            [
                "manual_review_route_brief.py",
                "--limit",
                str(args.manual_route_limit),
                "--preserve-order",
            ],
            45,
        ),
        (
            "consolidate_profile_enrichment_reviews",
            [
                "consolidate_profile_enrichment_reviews.py",
                "--limit",
                str(args.enrichment_consolidation_limit),
                "--json",
                *(
                    ["--clinic", args.enrichment_consolidation_clinic]
                    if args.enrichment_consolidation_clinic
                    else []
                ),
            ],
            45,
        ),
    ])
    if args.google_link_reconciliation or args.google_link_reconciliation_clinic:
        google_link_reconciliation_args = [
            "google_link_review_reconciliation.py",
            "--limit",
            str(args.google_link_reconciliation_limit),
            "--json",
        ]
        if args.google_link_reconciliation_clinic:
            google_link_reconciliation_args.extend(["--clinic", args.google_link_reconciliation_clinic])
        steps.append(("google_link_review_reconciliation", google_link_reconciliation_args, 45))
    if args.specialist_reconciliation or args.specialist_reconciliation_clinic:
        specialist_reconciliation_args = [
            "specialist_review_reconciliation.py",
            "--limit",
            str(args.specialist_reconciliation_limit),
            "--json",
        ]
        if args.specialist_reconciliation_clinic:
            specialist_reconciliation_args.extend(["--clinic", args.specialist_reconciliation_clinic])
        steps.append(("specialist_review_reconciliation", specialist_reconciliation_args, 45))
    if args.specialist_claim_proposals or args.specialist_claim_proposals_clinic:
        specialist_claim_proposal_args = [
            "export_specialist_claim_proposals.py",
            "--limit",
            str(args.specialist_claim_proposal_limit),
            "--json",
        ]
        if args.specialist_claim_proposals_clinic:
            specialist_claim_proposal_args.extend(["--clinic", args.specialist_claim_proposals_clinic])
        steps.append(("export_specialist_claim_proposals", specialist_claim_proposal_args, 45))
    steps.extend([
        (
            "admin_digest",
            ["admin_digest.py", "--limit", str(args.digest_limit), "--json"],
            45,
        ),
        (
            "evaluate_claim_rules",
            ["evaluate_claim_rules.py", "--limit", str(args.claim_limit), "--json"],
            45,
        ),
    ])
    if args.strict_editorial:
        steps.append(
            (
                "check_operational_limits_strict",
                ["check_operational_limits.py", "--strict-editorial"],
                45,
            )
        )
    if args.production_health:
        steps.append(
            (
                "check_production_health",
                [
                    "check_production_health.py",
                    "--base-url",
                    args.production_base_url,
                    "--timeout",
                    str(args.production_timeout),
                    "--json",
                ],
                max(45, args.production_timeout * 6),
            )
        )
    clinic_visibility_query = args.clinic_visibility_clinic.strip()
    if args.clinic_visibility or clinic_visibility_query:
        if not clinic_visibility_query:
            clinic_visibility_query = (args.public_freshness_clinic or args.public_freshness_slug or "").strip()
        if clinic_visibility_query:
            steps.append(
                (
                    "clinic_public_visibility_report",
                    [
                        "clinic_public_visibility_report.py",
                        "--clinic",
                        clinic_visibility_query,
                        "--base-url",
                        args.production_base_url,
                        "--timeout",
                        str(args.production_timeout),
                        "--missing-limit",
                        str(args.clinic_visibility_missing_limit),
                        "--json",
                    ],
                    max(45, args.production_timeout * 10),
                )
            )
    if args.public_freshness:
        command = [
            "check_public_site_freshness.py",
            "--base-url",
            args.production_base_url,
            "--timeout",
            str(args.production_timeout),
            "--missing-limit",
            str(args.public_freshness_missing_limit),
            "--json",
        ]
        if args.public_freshness_slug:
            command += ["--slug", args.public_freshness_slug]
        if args.public_freshness_clinic:
            command += ["--clinic", args.public_freshness_clinic]
        steps.append(
            (
                "check_public_site_freshness",
                command,
                max(45, args.production_timeout * 8),
            )
        )
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-safe", action="store_true", help="Run safe internal writes; never publish or edit clinics.")
    parser.add_argument("--review-limit", type=int, default=100)
    parser.add_argument("--seed-source-limit", type=int, default=20)
    parser.add_argument("--team-source-limit", type=int, default=0, help="Optional discovery of official team/about source pages.")
    parser.add_argument("--team-source-clinic-slug", help="Limit optional team-source discovery to one clinic.")
    parser.add_argument("--team-source-max-links", type=int, default=3)
    parser.add_argument("--google-link-limit", type=int, default=0, help="Optional discovery of official Google Maps/review links.")
    parser.add_argument("--google-link-clinic-slug", help="Limit optional Google-link discovery to one clinic.")
    parser.add_argument("--google-link-replace-existing", action="store_true", help="Refresh matching open review cards.")
    parser.add_argument(
        "--google-link-allow-multiple-open-clinic-reviews",
        action="store_true",
        help="Allow Google-link proposals even when another enrichment card is open for the same clinic.",
    )
    parser.add_argument("--source-limit", type=int, default=40)
    parser.add_argument("--monitor-limit", type=int, default=40)
    parser.add_argument("--source-change-limit", type=int, default=10)
    parser.add_argument("--source-shadow-limit", type=int, default=0, help="Optional saved-source shadow extraction batch.")
    parser.add_argument("--source-shadow-clinic-slug", help="Limit optional saved-source batch to one clinic.")
    parser.add_argument("--source-shadow-replace-existing", action="store_true", help="Refresh matching open review cards.")
    parser.add_argument(
        "--extract-profile-job",
        action="store_true",
        help="Optionally process one queued EXTRACT_CLINIC_PROFILE job created from a review source URL.",
    )
    parser.add_argument(
        "--discovery-recommendation-job",
        action="store_true",
        help="Optionally process one queued DISCOVER_CLINIC recommendation that already has an official URL.",
    )
    parser.add_argument(
        "--extract-profile-job-replace-existing",
        action="store_true",
        help="Refresh an existing enrichment card for the same review-supplied source URL.",
    )
    parser.add_argument(
        "--extract-profile-job-allow-multiple-open-clinic-reviews",
        action="store_true",
        help="Allow the review-supplied source URL to create a card even if the clinic already has another enrichment card.",
    )
    parser.add_argument("--digest-limit", type=int, default=8)
    parser.add_argument("--claim-limit", type=int, default=100)
    parser.add_argument("--blocking-claim-limit", type=int, default=20)
    parser.add_argument("--snapshot-retention-days", type=int, default=180)
    parser.add_argument("--snapshot-keep-latest", type=int, default=3)
    parser.add_argument("--snapshot-retention-limit", type=int, default=8)
    parser.add_argument("--source-coverage-limit", type=int, default=12)
    parser.add_argument("--profile-completeness-limit", type=int, default=12)
    parser.add_argument(
        "--publication-readiness",
        action="store_true",
        help="Optionally summarize publication blockers across clinics; read-only.",
    )
    parser.add_argument("--publication-readiness-clinic", default="", help="Clinic name or slug for publication-readiness diagnostics.")
    parser.add_argument("--publication-readiness-limit", type=int, default=8)
    parser.add_argument("--backlog-brief-limit", type=int, default=8)
    parser.add_argument("--manual-route-limit", type=int, default=30, help="Maximum open review routes to summarize.")
    parser.add_argument("--enrichment-consolidation-limit", type=int, default=8)
    parser.add_argument("--enrichment-consolidation-clinic", default="", help="Clinic name or slug for duplicate enrichment consolidation.")
    parser.add_argument(
        "--google-link-reconciliation",
        action="store_true",
        help="Optionally reconcile open Google Maps/review proposals; read-only.",
    )
    parser.add_argument("--google-link-reconciliation-clinic", default="", help="Clinic name, slug or review-title fragment for Google link reconciliation.")
    parser.add_argument("--google-link-reconciliation-limit", type=int, default=8)
    parser.add_argument(
        "--specialist-reconciliation",
        action="store_true",
        help="Optionally reconcile published/proposed/internal specialists; read-only.",
    )
    parser.add_argument("--specialist-reconciliation-clinic", default="", help="Clinic name or slug for specialist reconciliation.")
    parser.add_argument("--specialist-reconciliation-limit", type=int, default=5)
    parser.add_argument(
        "--specialist-claim-proposals",
        action="store_true",
        help="Optionally summarize private proposal batches from internal specialist evidence; read-only.",
    )
    parser.add_argument("--specialist-claim-proposals-clinic", default="", help="Clinic name or slug for private specialist proposals.")
    parser.add_argument("--specialist-claim-proposal-limit", type=int, default=8)
    parser.add_argument("--fetch-timeout", type=int, default=12)
    parser.add_argument(
        "--production-health",
        action="store_true",
        help="Optionally check public production URLs; read-only and network-dependent.",
    )
    parser.add_argument(
        "--public-freshness",
        action="store_true",
        help="Optionally compare Supabase public feed with deployed clinic pages; read-only and network-dependent.",
    )
    parser.add_argument("--public-freshness-slug", default="", help="Limit public freshness to one clinic slug.")
    parser.add_argument("--public-freshness-clinic", default="", help="Limit public freshness to clinics matching a normal name, city or slug.")
    parser.add_argument("--public-freshness-missing-limit", type=int, default=8)
    parser.add_argument(
        "--clinic-visibility",
        action="store_true",
        help="Optionally explain one clinic's public visibility state; read-only and network-dependent.",
    )
    parser.add_argument("--clinic-visibility-clinic", default="", help="Clinic name or slug for the visibility diagnostic.")
    parser.add_argument("--clinic-visibility-missing-limit", type=int, default=30)
    parser.add_argument(
        "--strict-editorial",
        action="store_true",
        help="Optionally fail on sensitive ranking/prize/comparison language that needs Daniel.",
    )
    parser.add_argument(
        "--plain-brief",
        action="store_true",
        help="Print only Daniel's plain-language cycle brief instead of the technical JSON.",
    )
    parser.add_argument(
        "--max-open-reviews-for-safe-writes",
        type=int,
        default=DEFAULT_SAFE_WRITE_REVIEW_BACKLOG_STOP,
        help="In apply-safe mode, skip review-card writing steps once open reviews enter the near-full zone. Use 0 to disable.",
    )
    parser.add_argument("--production-base-url", default="https://www.vitalarga.com")
    parser.add_argument("--production-timeout", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if min(
        args.review_limit,
        args.seed_source_limit,
        args.team_source_limit,
        args.google_link_limit,
        args.source_limit,
        args.monitor_limit,
        args.source_change_limit,
        args.source_shadow_limit,
        args.digest_limit,
        args.claim_limit,
        args.blocking_claim_limit,
        args.snapshot_retention_days,
        args.snapshot_keep_latest,
        args.snapshot_retention_limit,
        args.source_coverage_limit,
        args.profile_completeness_limit,
        args.publication_readiness_limit,
        args.manual_route_limit,
        args.enrichment_consolidation_limit,
        args.google_link_reconciliation_limit,
        args.specialist_reconciliation_limit,
        args.specialist_claim_proposal_limit,
        args.public_freshness_missing_limit,
        args.clinic_visibility_missing_limit,
        args.max_open_reviews_for_safe_writes,
    ) < 0:
        raise SystemExit("limits must be zero or greater.")
    if args.team_source_max_links < 1:
        raise SystemExit("--team-source-max-links must be at least 1.")
    if min(
        args.review_limit,
        args.seed_source_limit,
        args.source_limit,
        args.monitor_limit,
        args.source_change_limit,
        args.digest_limit,
        args.claim_limit,
        args.blocking_claim_limit,
        args.snapshot_retention_days,
        args.snapshot_keep_latest,
        args.snapshot_retention_limit,
        args.source_coverage_limit,
        args.profile_completeness_limit,
        args.publication_readiness_limit,
        args.manual_route_limit,
        args.enrichment_consolidation_limit,
        args.google_link_reconciliation_limit,
        args.specialist_reconciliation_limit,
        args.specialist_claim_proposal_limit,
    ) < 1:
        raise SystemExit("limits must be at least 1.")
    if args.fetch_timeout < 3 or args.fetch_timeout > 60:
        raise SystemExit("--fetch-timeout must be between 3 and 60 seconds.")
    if args.production_timeout < 3 or args.production_timeout > 60:
        raise SystemExit("--production-timeout must be between 3 and 60 seconds.")
    if args.public_freshness_missing_limit < 1 or args.public_freshness_missing_limit > 30:
        raise SystemExit("--public-freshness-missing-limit must be between 1 and 30.")
    if args.clinic_visibility_missing_limit < 1 or args.clinic_visibility_missing_limit > 30:
        raise SystemExit("--clinic-visibility-missing-limit must be between 1 and 30.")
    if args.clinic_visibility and not (args.clinic_visibility_clinic or args.public_freshness_clinic or args.public_freshness_slug):
        raise SystemExit("--clinic-visibility needs --clinic-visibility-clinic or a public freshness clinic/slug.")

    steps = []
    review_card_writes_allowed = True
    backlog_guard_reason = ""
    if args.apply_safe and args.max_open_reviews_for_safe_writes:
        preflight = run_step(
            "preflight_review_backlog",
            ["admin_digest.py", "--limit", "1", "--json"],
            45,
        )
        steps.append(preflight)
        if not preflight["ok"]:
            output = {
                "mode": "apply_safe",
                "ok": False,
                "steps": steps,
            }
            output["daniel_brief"] = build_cycle_brief(output)
            if args.plain_brief:
                print(format_cycle_brief(output["daniel_brief"]), end="")
            else:
                print(json.dumps(output, ensure_ascii=False, indent=2))
            return 1
        open_reviews = open_review_count_from_digest(safe_step_summary(preflight))
        if open_reviews >= args.max_open_reviews_for_safe_writes:
            review_card_writes_allowed = False
            backlog_guard_reason = (
                f"{open_reviews} revisiones abiertas; limite seguro "
                f"{args.max_open_reviews_for_safe_writes}."
            )

    for name, command_args, timeout in build_steps(args):
        if args.apply_safe and not review_card_writes_allowed and name in REVIEW_CARD_CREATING_STEPS:
            steps.append(skipped_step(name, backlog_guard_reason))
            continue
        step = run_step(name, command_args, timeout)
        steps.append(step)
        if not step["ok"]:
            break

    output = {
        "mode": "apply_safe" if args.apply_safe else "dry_run",
        "ok": all(step["ok"] for step in steps),
        "steps": steps,
    }
    output["daniel_brief"] = build_cycle_brief(output)
    if args.plain_brief:
        print(format_cycle_brief(output["daniel_brief"]), end="")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
