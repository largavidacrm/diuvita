#!/usr/bin/env python3
"""Checks for the read-only location coverage report."""

from measure_location_coverage import (
    first_location_claim,
    first_location_proposal,
    format_location_coverage,
    format_location_claim_row,
    format_location_proposal_row,
    format_location_row,
    location_name,
    location_next_step,
    location_review_backlog_guard,
    next_location_action,
    pct,
    safe_limit,
    should_defer_location_review_creation,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T20:20:00+00:00",
        "summary": {
            "visible_clinics": 4,
            "open_reviews": 40,
            "safe_write_limit": 50,
            "clinics_with_locations": 2,
            "multi_location_clinics": 1,
            "total_locations": 3,
            "locations_with_address": 3,
            "locations_missing_address": 0,
            "locations_with_google_maps_profile": 1,
            "locations_missing_google_maps_profile": 2,
            "clinics_with_location_proposals": 1,
            "proposed_location_rows": 2,
            "clinics_with_location_claims": 1,
            "internal_location_rows": 2,
        },
        "next_location_target": {
            "slug": "clinic-a",
            "clinic_name": "Clinic A",
            "clinic_city": "Madrid",
            "status": "published",
            "location_index": 1,
            "location_label": "Sede principal",
            "clinic_location_count": 2,
            "pending_fields": ["Google Maps de clínica"],
            "pending_count": 1,
        },
        "pending_locations": [
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "clinic_city": "Madrid",
                "status": "published",
                "location_index": 1,
                "location_label": "Sede principal",
                "clinic_location_count": 2,
                "pending_fields": ["Google Maps de clínica"],
                "pending_count": 1,
            },
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "clinic_city": "Madrid",
                "status": "published",
                "location_index": 2,
                "location_label": "",
                "clinic_location_count": 2,
                "pending_fields": ["Google Maps de clínica"],
                "pending_count": 1,
            },
        ],
        "pending_location_proposals": [
            {
                "slug": "clinic-c",
                "clinic_name": "Clinic C",
                "clinic_city": "Barcelona",
                "status": "published",
                "open_review_count": 2,
                "proposed_location_count": 2,
            }
        ],
        "pending_location_claims": [
            {
                "slug": "clinic-d",
                "clinic_name": "Clinic D",
                "clinic_city": "Valencia",
                "status": "published",
                "claim_count": 1,
                "location_claim_count": 2,
            }
        ],
    }
    output = format_location_coverage(report)

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(250) == 100, "limit should have an upper bound")
    check(pct(1, 4) == "25%", "percentage formatting missing")
    check(location_review_backlog_guard(report["summary"]) == "con margen: 40/50 revisiones abiertas", "backlog guard label missing")
    check(not should_defer_location_review_creation(report["summary"]), "base report should allow location review creation")
    check(location_name(report["pending_locations"][1]) == "Sede adicional", "fallback label should avoid numbering")
    check(
        next_location_action(report)
        == "Revisar Sede principal de Clinic A: añadir el perfil real de Google Business de Clinic A para Sede principal; no usar búsqueda, ruta ni enlace de dirección",
        "next location action missing",
    )
    check(
        location_next_step(report["pending_locations"][0])
        == "añadir el perfil real de Google Business de Clinic A para Sede principal; no usar búsqueda, ruta ni enlace de dirección",
        "direct Google Business next step missing",
    )
    check("# Vitalarga location coverage" in output, "title missing")
    check("Clínicas visibles: 4" in output, "visible clinic count missing")
    check("Clínicas con varias sedes: 1" in output, "multi-location count missing")
    check("Sedes medidas: 3" in output, "location count missing")
    check("Sedes con Google Maps de clínica: 1/3 (33%)" in output, "Maps coverage missing")
    check("valoraciones Google" not in output, "Google reviews should no longer be a location coverage field")
    check("Bandeja de revisión: con margen: 40/50 revisiones abiertas" in output, "backlog guard output missing")
    check("Clínicas con sedes propuestas en bandeja: 1" in output, "location proposal clinic count missing")
    check("Sedes propuestas en bandeja: 2" in output, "location proposal count missing")
    check("Clínicas con sedes detectadas internas: 1" in output, "location claim clinic count missing")
    check("Sedes detectadas internas: 2" in output, "location claim count missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("Siguiente acción" in output, "next action section missing")
    check("Clinic A · Madrid · publicada · Sede adicional · 2 sedes" in output, "pending location row missing")
    check("siguiente: añadir el perfil real de Google Business de Clinic A para Sede adicional" in output, "row next step missing")
    check("Sedes propuestas en bandeja" in output, "location proposals section missing")
    check("Clinic C · Barcelona · publicada · 2 sedes detectadas · 2 revisiones abiertas" in output, "location proposal row missing")
    check("cargar sedes detectadas en el editor" in output, "location proposal next step missing")
    check("Sedes detectadas internas" in output, "internal location claims section missing")
    check("Clinic D · Valencia · publicada · 2 sedes detectadas internas · 1 evidencia" in output, "internal location claim row missing")
    check("convertir en propuesta revisable" in output, "internal location claim next step missing")
    check(first_location_proposal(report)["clinic_name"] == "Clinic C", "first location proposal missing")
    check(first_location_claim(report)["clinic_name"] == "Clinic D", "first location claim missing")
    check(format_location_proposal_row(report["pending_location_proposals"][0]).startswith("- Clinic C"), "proposal formatter missing")
    check(format_location_claim_row(report["pending_location_claims"][0]).startswith("- Clinic D"), "claim formatter missing")
    single_claim_row = dict(report["pending_location_claims"][0], location_claim_count=1)
    check("1 sede detectada interna" in format_location_claim_row(single_claim_row), "singular internal location claim label missing")
    no_explicit_report = dict(report, next_location_target={}, pending_locations=[])
    check(
        next_location_action(no_explicit_report) == "Revisar sedes propuestas de Clinic C: 2 sedes detectadas en bandeja",
        "next action should fall back to proposed locations",
    )
    claims_only_report = dict(no_explicit_report, pending_location_proposals=[])
    check(
        next_location_action(claims_only_report) == "Preparar revisión de sedes para Clinic D: 2 sedes detectadas internas",
        "next action should fall back to internal location claims",
    )
    backlogged_report = dict(claims_only_report, summary=dict(report["summary"], open_reviews=48))
    check(
        location_review_backlog_guard(backlogged_report["summary"]) == "cerca del freno: 48/50 revisiones abiertas",
        "near-limit backlog guard missing",
    )
    check(should_defer_location_review_creation(backlogged_report["summary"]), "near-limit report should defer new cards")
    check(
        next_location_action(backlogged_report) == "Bajar bandeja antes de crear propuestas de sedes: Clinic D tiene 2 sedes detectadas internas",
        "backlogged next action should defer location review creation",
    )
    check(
        "primero bajar la bandeja" in format_location_claim_row(report["pending_location_claims"][0], backlogged_report["summary"]),
        "backlogged claim row should explain deferred proposal creation",
    )
    check("Sede 1" not in output and "Sede 2" not in output, "location output should avoid numbered labels")
    address_row = dict(report["pending_locations"][0], pending_fields=["Dirección", "Google Maps de clínica"])
    check(
        location_next_step(address_row) == "completar la dirección exacta de Sede principal en Clinic A",
        "address should be the first location next step",
    )
    check("no ordena clínicas por calidad" in output, "no-ranking note missing")
    check(format_location_row(report["pending_locations"][0]).startswith("- Clinic A"), "row formatter missing")
    print("OK location coverage: explicit sede gaps are readable")


if __name__ == "__main__":
    main()
