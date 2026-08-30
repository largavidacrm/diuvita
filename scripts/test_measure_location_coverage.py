#!/usr/bin/env python3
"""Checks for the read-only location coverage report."""

from measure_location_coverage import (
    format_location_coverage,
    format_location_row,
    location_name,
    next_location_action,
    pct,
    safe_limit,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T20:20:00+00:00",
        "summary": {
            "visible_clinics": 4,
            "clinics_with_locations": 2,
            "multi_location_clinics": 1,
            "total_locations": 3,
            "locations_with_address": 3,
            "locations_missing_address": 0,
            "locations_with_google_maps_profile": 1,
            "locations_missing_google_maps_profile": 2,
            "locations_with_google_reviews": 0,
            "locations_missing_google_reviews": 3,
        },
        "next_location_target": {
            "slug": "clinic-a",
            "clinic_name": "Clinic A",
            "clinic_city": "Madrid",
            "status": "published",
            "location_index": 1,
            "location_label": "Sede principal",
            "clinic_location_count": 2,
            "pending_fields": ["Google Maps de clínica", "Valoraciones Google"],
            "pending_count": 2,
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
                "pending_fields": ["Google Maps de clínica", "Valoraciones Google"],
                "pending_count": 2,
            },
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "clinic_city": "Madrid",
                "status": "published",
                "location_index": 2,
                "location_label": "",
                "clinic_location_count": 2,
                "pending_fields": ["Valoraciones Google"],
                "pending_count": 1,
            },
        ],
    }
    output = format_location_coverage(report)

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(250) == 100, "limit should have an upper bound")
    check(pct(1, 4) == "25%", "percentage formatting missing")
    check(location_name(report["pending_locations"][1]) == "Sede adicional", "fallback label should avoid numbering")
    check(
        next_location_action(report) == "Revisar Sede principal de Clinic A: pendiente Google Maps de clínica, Valoraciones Google",
        "next location action missing",
    )
    check("# Vitalarga location coverage" in output, "title missing")
    check("Clínicas visibles: 4" in output, "visible clinic count missing")
    check("Clínicas con varias sedes: 1" in output, "multi-location count missing")
    check("Sedes medidas: 3" in output, "location count missing")
    check("Sedes con Google Maps de clínica: 1/3 (33%)" in output, "Maps coverage missing")
    check("Sedes con valoraciones Google: 0/3 (0%)" in output, "reviews coverage missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("Siguiente acción" in output, "next action section missing")
    check("Clinic A · Madrid · publicada · Sede adicional · 2 sedes" in output, "pending location row missing")
    check("Sede 1" not in output and "Sede 2" not in output, "location output should avoid numbered labels")
    check("no ordena clínicas por calidad" in output, "no-ranking note missing")
    check(format_location_row(report["pending_locations"][0]).startswith("- Clinic A"), "row formatter missing")
    print("OK location coverage: explicit sede gaps are readable")


if __name__ == "__main__":
    main()
