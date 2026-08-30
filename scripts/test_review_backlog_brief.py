#!/usr/bin/env python3
"""Checks for the read-only review backlog brief."""

from review_backlog_brief import (
    backlog_guard,
    first_backlog_action,
    format_backlog,
    format_clinic_workgroup,
    safe_limit,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T16:10:00+00:00",
        "summary": {
            "open_reviews": 48,
            "open_enrichment_reviews": 16,
            "duplicate_enrichment_clinics": 2,
            "duplicate_enrichment_reviews": 5,
            "safe_write_limit": 50,
        },
        "review_type_summary": [
            {"review_type": "mejoras de ficha", "open_count": 16, "max_priority": 80},
            {"review_type": "clinicas candidatas", "open_count": 8, "max_priority": 90},
            {"review_type": "claims bloqueantes", "open_count": 4, "max_priority": 85},
            {"review_type": "cambios de fuente", "open_count": 1, "max_priority": 70},
        ],
        "clinic_workgroups": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 5,
                "blocking_claim_reviews": 1,
                "quality_reviews": 1,
                "enrichment_reviews": 3,
                "source_change_reviews": 0,
                "candidate_reviews": 0,
                "max_priority": 85,
                "oldest_created_at": "2026-08-30T08:30:00+00:00",
            },
            {
                "clinic_name": "Kairos Longevity Clinic",
                "clinic_slug": "kairos-longevity-clinic",
                "city": "Madrid",
                "clinic_status": "published",
                "card_count": 4,
                "blocking_claim_reviews": 2,
                "quality_reviews": 0,
                "enrichment_reviews": 2,
                "source_change_reviews": 0,
                "candidate_reviews": 0,
                "max_priority": 85,
                "oldest_created_at": "2026-08-30T09:30:00+00:00",
            },
        ],
        "duplicate_enrichment": [
            {
                "clinic_name": "Sensabell",
                "clinic_slug": "sensabell",
                "city": "Valencia",
                "clinic_status": "published",
                "card_count": 3,
                "max_priority": 80,
                "oldest_created_at": "2026-08-30T09:00:00+00:00",
            },
            {
                "clinic_name": "Kairos Longevity Clinic",
                "clinic_slug": "kairos-longevity-clinic",
                "city": "Madrid",
                "clinic_status": "published",
                "card_count": 2,
                "max_priority": 70,
                "oldest_created_at": "2026-08-30T10:00:00+00:00",
            },
        ],
    }
    output = format_backlog(report)

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(100) == 50, "limit should have an upper bound")
    check(backlog_guard(report["summary"]) == "cerca del freno: 48/50 abiertas", "guard label missing")
    check(first_backlog_action(report) == "Revisar Sensabell: tiene 3 mejoras abiertas", "first action missing")
    check(
        format_clinic_workgroup(report["clinic_workgroups"][0])
        == "- Sensabell · Valencia · publicada · 5 tarjetas · 1 claim bloqueante / 3 mejoras / 1 auditoría · P85 · más antigua 2026-08-30 08:30",
        "clinic workgroup formatting missing",
    )
    check("# Diuvita: atascos de bandeja" in output, "title missing")
    check("Revisiones abiertas: 48" in output, "open count missing")
    check("Mejoras de ficha abiertas: 16" in output, "enrichment count missing")
    check("claims bloqueantes: 4 abiertas; máxima prioridad P85" in output, "blocking claim type missing")
    check("cambios de fuente: 1 abierta; máxima prioridad P70" in output, "singular open label missing")
    check("Clínicas con varias mejoras abiertas: 2" in output, "duplicate clinic count missing")
    check("Tarjetas en grupos duplicados: 5" in output, "duplicate card count missing")
    check("Freno de bandeja: cerca del freno: 48/50 abiertas" in output, "guard line missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("## Trabajar por clínica" in output, "clinic workgroup section missing")
    check("Sensabell · Valencia · publicada · 5 tarjetas" in output, "clinic workgroup missing")
    check("Kairos Longevity Clinic · Madrid · publicada · 4 tarjetas" in output, "second workgroup missing")
    check("2 claims bloqueantes / 2 mejoras" in output, "workgroup type counts missing")
    check("Sensabell · Valencia · publicada · 3 tarjetas · P80" in output, "duplicate group missing")
    check("No hay grupos duplicados" not in output, "should not show empty duplicate state")
    check("no descarta ni resuelve tarjetas" in output, "safety note missing")

    empty_report = {
        "summary": {"open_reviews": 0, "safe_write_limit": 50},
        "review_type_summary": [],
        "clinic_workgroups": [],
        "duplicate_enrichment": [],
    }
    check(first_backlog_action(empty_report) == "No hay revisiones abiertas", "empty action missing")
    check("No hay grupos de revisión por clínica" in format_backlog(empty_report), "empty workgroup state missing")
    check("No hay grupos duplicados" in format_backlog(empty_report), "empty duplicate state missing")
    print("OK review backlog brief: duplicate pressure is readable")


if __name__ == "__main__":
    main()
