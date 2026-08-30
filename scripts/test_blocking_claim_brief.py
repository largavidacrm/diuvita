#!/usr/bin/env python3
"""Checks for Daniel's blocking-claim brief."""
from blocking_claim_brief import (
    blocker_status,
    compact_field_rows,
    field_label,
    format_brief,
    recommended_step,
    source_host,
    summarize_group,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_group():
    return {
        "clinic_slug": "clinic",
        "clinic_name": "Clinic",
        "clinic_city": "Barcelona",
        "clinic_country": "España",
        "website": "https://clinic.example",
        "claims": [
            {
                "field_path": "contact.phone",
                "verification_status": "review",
                "blocker_status": "without_source",
                "confidence": 0.6,
                "source_url": None,
                "created_at": "2026-08-30T12:00:00+00:00",
            },
            {
                "field_path": "medical_claims.list",
                "verification_status": "conflict",
                "blocker_status": "conflict",
                "confidence": 0.95,
                "source_url": "https://www.clinic.example/evidence",
                "created_at": "2026-08-30T13:00:00+00:00",
            },
        ],
    }


def main():
    group = sample_group()
    summary = summarize_group(group)
    output = format_brief([group])

    check(blocker_status(group["claims"][0]) == "without_source", "blocker status should prefer blocker_status")
    check(field_label("contact.phone") == "Teléfono", "field label missing")
    check(source_host("https://www.clinic.example/evidence") == "clinic.example", "source host should be compact")
    check(summary["priority"] == 95, "conflict should make the case highest priority")
    check(summary["statuses"]["conflict"] == 1, "conflict count missing")
    check(
        recommended_step(summary["statuses"]) == "comparar la evidencia y elegir el dato correcto antes de publicar",
        "recommended conflict step missing",
    )
    check(
        recommended_step({"without_source": 1}) == "buscar una fuente oficial o quitar el dato propuesto",
        "recommended source step missing",
    )
    duplicated_fields = compact_field_rows([summary["fields"][0], summary["fields"][0]])
    check(duplicated_fields[0]["count"] == 2, "repeated claim fields should be compacted")
    check("# Vitalarga: claims bloqueantes" in output, "title missing")
    check("Clínicas afectadas: 1" in output, "clinic count missing")
    check("Claims a revisar: 2" in output, "claim count missing")
    check("Clinic · Barcelona, España" in output, "clinic heading missing")
    check("Prioridad: P95 · 2 claims · 1 en conflicto · 1 sin fuente" in output, "status summary missing")
    check("Paso recomendado: comparar la evidencia" in output, "recommended step line missing")
    check("Campo: Claims médicos · en conflicto · confianza 95% · fuente clinic.example" in output, "field line missing")
    check("Seguridad: este brief no publica" in output, "safety line missing")
    print("OK blocking claim brief: Daniel summary is readable")


if __name__ == "__main__":
    main()
