#!/usr/bin/env python3
"""Checks for the read-only profile-completeness report."""

from measure_profile_completeness import format_completeness, next_profile_action, pct, safe_limit


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T16:20:00+00:00",
        "summary": {
            "visible_clinics": 4,
            "profiles_without_pending_fields": 1,
            "profiles_with_pending_fields": 3,
            "with_open_quality_reviews": 2,
        },
        "field_summary": [
            {"field": "summary", "label": "Resumen suficiente", "present": 3, "pending": 1},
            {"field": "website", "label": "Web oficial", "present": 4, "pending": 0},
            {"field": "google_maps", "label": "Google Maps de clínica", "present": 1, "pending": 3},
            {"field": "specialists", "label": "Especialistas publicados", "present": 1, "pending": 3},
            {"field": "years_in_practice", "label": "Años en ejercicio", "present": 1, "pending": 3},
            {"field": "specialists_count", "label": "Número de especialistas", "present": 2, "pending": 2},
            {"field": "team_credentialing_visible", "label": "Colegiación visible", "present": 1, "pending": 3},
            {"field": "public_pricing", "label": "Precio público", "present": 0, "pending": 4},
        ],
        "pending_profiles": [
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "city": "Madrid",
                "status": "published",
                "pending_fields": ["Email o teléfono", "Especialistas publicados"],
                "pending_count": 2,
                "next_pending_field": "Email o teléfono",
                "open_quality_reviews": 0,
                "open_profile_reviews": 1,
                "open_source_change_reviews": 0,
                "open_relevant_reviews": 1,
            }
        ],
        "next_profile_target": {
            "slug": "clinic-a",
            "clinic_name": "Clinic A",
            "city": "Madrid",
            "status": "published",
            "pending_fields": ["Email o teléfono", "Especialistas publicados"],
            "pending_count": 2,
            "next_pending_field": "Email o teléfono",
            "open_quality_reviews": 0,
            "open_profile_reviews": 1,
            "open_source_change_reviews": 0,
            "open_relevant_reviews": 1,
        },
    }
    output = format_completeness(report)

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(250) == 100, "limit should have an upper bound")
    check(pct(1, 4) == "25%", "percentage formatting missing")
    check(
        next_profile_action(report) == "Revisar Clinic A: ya tiene 1 revisión abierta relacionada. Primer campo: Email o teléfono",
        "next profile action missing",
    )
    check("# Vitalarga profile completeness" in output, "title missing")
    check("Clínicas visibles: 4" in output, "visible count missing")
    check("Sin campos pendientes medidos: 1 (25%)" in output, "complete count missing")
    check("Con campos pendientes medidos: 3 (75%)" in output, "pending count missing")
    check("Con revisión interna de calidad abierta: 2" in output, "quality-review count missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("Siguiente acción" in output, "next action section missing")
    check("Primer campo: Email o teléfono" in output, "next pending field missing")
    check("Resumen suficiente: 3 listos / 1 pendientes" in output, "field summary missing")
    check("Google Maps de clínica: 1 listos / 3 pendientes" in output, "Google Maps field missing")
    check("Valoraciones Google" not in output, "Google reviews should no longer be a profile-completeness field")
    check("Especialistas publicados: 1 listos / 3 pendientes" in output, "specialist field missing")
    check("Años en ejercicio: 1 listos / 3 pendientes" in output, "years-in-practice field missing")
    check("Número de especialistas: 2 listos / 2 pendientes" in output, "specialist-count field missing")
    check("Colegiación visible: 1 listos / 3 pendientes" in output, "credentialing field missing")
    check("Precio público: 0 listos / 4 pendientes" in output, "public pricing field missing")
    check(
        "Clinic A · Madrid · publicada · pendiente: Email o teléfono, Especialistas publicados · 1 revisión abierta" in output,
        "pending profile line missing",
    )
    check("no ordena clínicas por calidad" in output, "no-ranking note missing")
    print("OK profile completeness: report is read-only")


if __name__ == "__main__":
    main()
