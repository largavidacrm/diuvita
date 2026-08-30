#!/usr/bin/env python3
"""Checks for the read-only source coverage report."""

from measure_source_coverage import (
    format_source_coverage,
    next_source_action,
    pct,
    safe_limit,
    status_label,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T16:30:00+00:00",
        "summary": {
            "visible_clinics": 4,
            "clinics_with_sources": 3,
            "clinics_without_sources": 1,
            "clinics_with_hydrated_sources": 2,
            "clinics_without_hydrated_sources": 2,
            "clinics_with_claims": 2,
            "clinics_without_claims": 2,
            "clinics_needing_source_work": 3,
            "claims_with_source": 12,
            "claims_without_source": 2,
            "blocking_claims": 3,
        },
        "next_source_target": {
            "slug": "clinic-b",
            "clinic_name": "Clinic B",
            "city": "Barcelona",
            "status": "preliminary",
            "source_records": 2,
            "hydrated_source_records": 1,
            "source_snapshots": 1,
            "total_claims": 4,
            "claims_with_source": 3,
            "claims_without_source": 1,
            "blocking_claims": 1,
        },
        "needs_source_work": [
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "city": "Madrid",
                "status": "published",
                "source_records": 0,
                "hydrated_source_records": 0,
                "source_snapshots": 0,
                "total_claims": 0,
                "claims_with_source": 0,
                "claims_without_source": 0,
                "blocking_claims": 0,
            },
            {
                "slug": "clinic-b",
                "clinic_name": "Clinic B",
                "city": "Barcelona",
                "status": "preliminary",
                "source_records": 2,
                "hydrated_source_records": 1,
                "source_snapshots": 1,
                "total_claims": 4,
                "claims_with_source": 3,
                "claims_without_source": 1,
                "blocking_claims": 1,
            },
        ],
    }
    output = format_source_coverage(report)

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(250) == 100, "limit should have an upper bound")
    check(pct(1, 4) == "25%", "percentage formatting missing")
    check(status_label("published") == "publicada", "published label missing")
    check(next_source_action(report) == "Revisar 1 claim bloqueante de Clinic B", "next source action missing")
    check("# Vitalarga source coverage" in output, "title missing")
    check("Fichas visibles: 4" in output, "visible count missing")
    check("Con fuentes guardadas: 3/4 (75%)" in output, "source coverage missing")
    check("Con fuentes hidratadas: 2/4 (50%)" in output, "hydrated source coverage missing")
    check("Con claims internos: 2/4 (50%)" in output, "claim coverage missing")
    check("Necesitan trabajo de fuente: 3" in output, "source work count missing")
    check("Claims sin fuente: 2" in output, "claims without source missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("Siguiente acción" in output, "next action section missing")
    check("Clinic A · Madrid · publicada · fuentes 0/0 hidratadas" in output, "source row missing")
    check("Clinic B · Barcelona · preliminar · fuentes 1/2 hidratadas" in output, "preliminary row missing")
    check("1 sin fuente · 1 bloqueante" in output, "blocking source detail missing")
    check("no decide calidad" in output, "no-ranking note missing")

    no_source_report = {
        "next_source_target": {
            "clinic_name": "Clinic A",
            "source_records": 0,
            "hydrated_source_records": 0,
            "total_claims": 0,
            "claims_without_source": 0,
            "blocking_claims": 0,
        }
    }
    check(next_source_action(no_source_report) == "Añadir fuente oficial para Clinic A", "no-source action missing")

    hydrated_report = {
        "next_source_target": {
            "clinic_name": "Clinic C",
            "source_records": 2,
            "hydrated_source_records": 0,
            "total_claims": 0,
            "claims_without_source": 0,
            "blocking_claims": 0,
        }
    }
    check(next_source_action(hydrated_report) == "Hidratar 2 fuentes guardadas de Clinic C", "hydrate action missing")

    claims_report = {
        "next_source_target": {
            "clinic_name": "Clinic D",
            "source_records": 1,
            "hydrated_source_records": 1,
            "total_claims": 4,
            "claims_without_source": 2,
            "blocking_claims": 2,
        }
    }
    check(next_source_action(claims_report) == "Revisar 2 claims bloqueantes de Clinic D", "blocking action missing")
    print("OK source coverage: visible provenance gaps are readable")


if __name__ == "__main__":
    main()
