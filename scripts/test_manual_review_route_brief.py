#!/usr/bin/env python3
"""Checks manual review route briefs stay read-only and LLM-safe."""
from manual_review_route_brief import (
    ROUTE_BRIEF_SCHEMA_VERSION,
    compact_item_line,
    format_route_report,
    route_report,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def manual_quality_row():
    return {
        "id": "quality-1",
        "title": "Completar ficha: Tiara Health",
        "review_type": "clinic_quality_audit",
        "priority": 85,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "issues": [
                {"code": "missing_professionals", "label": "Faltan especialistas publicados"},
                {"code": "missing_contact", "label": "Falta email o teléfono"},
            ],
        },
        "clinic": {
            "id": "clinic-tiara",
            "slug": "tiara-health",
            "display_name": "Tiara Health",
            "city": "Marbella",
            "country": "España",
            "status": "preliminary",
            "current_data": {},
        },
    }


def source_without_context_row():
    return {
        "id": "blocked-1",
        "title": "Revisar valoraciones Google: Clinic",
        "review_type": "clinic_profile_enrichment",
        "priority": 60,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "source_url": "https://clinic.example/contacto",
            "proposed_fields": {
                "google_reviews_url": "https://www.google.com/maps/place/Clinic/reviews",
            },
        },
        "clinic": {"display_name": "Clinic", "current_data": {}},
    }


def context_ready_row():
    return {
        "id": "ready-1",
        "title": "Revisar extracción shadow: Unidad de Longevidad IMDA",
        "review_type": "clinic_profile_enrichment",
        "priority": 75,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "source_url": "https://imda.example/contacto",
            "from_review_id": "quality-previous",
            "human_supplied_source": True,
            "requested_fields": ["telefono"],
            "requested_field_labels": ["Teléfono principal"],
            "target_scope": "primary_target_first",
            "ui_route": "manual_review_banner_source_handoff",
            "allowed_output": "review_queue_proposal_only",
            "llm_boundary": "respect_source_job_context_scope",
            "proposed_fields": {
                "telefono": "916 000 000",
            },
        },
        "clinic": {
            "id": "clinic-1",
            "slug": "unidad-de-longevidad-imda",
            "display_name": "Unidad de Longevidad IMDA",
            "city": "Madrid",
            "country": "España",
            "status": "preliminary",
            "current_data": {"telefono": "915 111 111"},
        },
    }


def specialist_needs_source_row():
    return {
        "id": "specialist-source-1",
        "title": "Revisar especialistas: Tiara Health",
        "review_type": "clinic_profile_enrichment",
        "priority": 84,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "proposed_fields": {
                "profesionales": ["Dra. Example", "Dr. Example"],
            },
        },
        "clinic": {
            "id": "clinic-tiara",
            "slug": "tiara-health",
            "display_name": "Tiara Health",
            "city": "Marbella",
            "country": "España",
            "status": "preliminary",
            "current_data": {"profesionales": []},
        },
    }


def main():
    rows = [
        source_without_context_row(),
        context_ready_row(),
        specialist_needs_source_row(),
        manual_quality_row(),
    ]
    report = route_report(rows)
    check(report["schema_version"] == ROUTE_BRIEF_SCHEMA_VERSION, "schema version missing")
    check(report["writes_data"] is False, "route brief must not write data")
    check(report["calls_llm"] is False, "route brief must not call an LLM")
    check(report["decision_scope"] == "one_card_one_decision", "decision scope missing")
    check(report["summary"]["total_packets"] == 4, "total packet count missing")
    check(report["summary"]["manual_field_routes"] == 1, "manual field route count missing")
    check(report["summary"]["source_handoff_available"] == 2, "source handoff count missing")
    check(report["summary"]["manual_navigation_llm_ready"] == 1, "manual LLM navigation count missing")
    check(report["summary"]["source_only_reviewable"] == 1, "source-only reviewable count missing")
    check(report["summary"]["legacy_source_llm_ready"] == 1, "legacy source LLM-ready count missing")
    check(report["summary"]["blocked_without_operator_context"] == 0, "blocked source-only count missing")
    check(report["summary"]["direct_change_reviews"] == 2, "direct change count missing")

    first = report["items"][0]
    check(
        first["title"] == "Revisión manual: Tiara Health · Faltan especialistas publicados",
        "manual cards should show the active field first",
    )
    check(first["operator_action"] == "open_manual_field", "manual field action missing")
    check(first["manual_primary_target"]["key"] == "profesionales", "primary manual target missing")
    check(first["manual_primary_target"]["admin_target_id"] == "clinicProfessionals", "admin target missing")
    check(first["llm_help_scope"] == "manual_navigation_only", "manual LLM scope missing")
    check("publicados" in " ".join(first["manual_target_labels"]), "manual target labels missing")
    check(first["source_handoff"]["target_scope"] == "primary_target_first", "manual source handoff scope missing")

    by_id = {item["review_id"]: item for item in report["items"]}
    source_needed = by_id["specialist-source-1"]
    check(source_needed["operator_action"] == "request_official_source", "specialist source action missing")
    check(
        source_needed["source_handoff"]["target_scope"] == "specialist_source_only",
        "specialist source handoff should stay bounded",
    )
    source_only = by_id["blocked-1"]
    check(source_only["operator_action"] == "review_proposed_change_source_only", "source-only review action missing")
    check(source_only["llm_help_scope"] == "legacy_source_explicit_fields_only", "source-only LLM scope missing")
    ready = by_id["ready-1"]
    check(ready["operator_action"] == "review_proposed_change", "context-ready row should remain a direct proposal")
    check(ready["llm_help_scope"] == "prepare_suggestion_then_validate_locally", "strict LLM scope missing")

    compact = format_route_report(report, limit=3)
    check("# Rutas de revisión manual" in compact, "compact title missing")
    check("Abren campo directo: 1" in compact, "compact manual count missing")
    check("Permiten pasar URL oficial al agente: 2" in compact, "compact source handoff count missing")
    check("Fuentes heredadas listas con límites: 1" in compact, "compact legacy source count missing")
    check("Revisiones con fuente heredada: 1" in compact, "compact source-only reviewable count missing")
    check("Bloqueadas para LLM por fuente sin contexto: 0" in compact, "compact LLM block count missing")
    check("desde la propuesta, abrir Especialistas publicados en ficha" in compact, "compact manual field line missing")
    check("fuente heredada acotada para ayuda LLM" in compact, "compact source-only review line missing")
    check("solo creará propuesta revisable" in compact, "compact source safety line missing")
    check("... 1 tarjetas más" in compact, "compact overflow line missing")
    check("abrir Especialistas publicados" in compact_item_line(first), "compact item helper missing")

    source = __import__("pathlib").Path("scripts/manual_review_route_brief.py").read_text(encoding="utf-8")
    lowered = source.lower()
    for forbidden in ["insert into", " update ", " delete from", "admin_update_clinic", "admin_resolve_review_item"]:
        check(forbidden not in lowered, f"route brief should not write data: {forbidden}")

    print("OK manual review route brief: manual routes stay clear and read-only")


if __name__ == "__main__":
    main()
