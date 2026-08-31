#!/usr/bin/env python3
"""Checks for the read-only specialist coverage report."""

from measure_specialist_coverage import (
    clean_specialist_example,
    format_clinic_line,
    format_coverage,
    next_specialist_action,
    pct,
    prioritized_missing_rows,
    specialist_examples,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T15:20:00+00:00",
        "summary": {
            "visible_clinics": 4,
            "with_specialists": 1,
            "without_specialists": 3,
            "total_specialist_entries": 5,
            "clinics_with_specialist_claims": 2,
            "clinics_with_open_specialist_reviews": 1,
        },
        "missing_specialists": [
            {
                "slug": "clinic-a",
                "clinic_name": "Clinic A",
                "city": "Madrid",
                "status": "published",
                "specialist_claims": 2,
                "specialist_examples": ["Dra. Maria Uno", "Dr. Luis Dos", "Dr. Luis Dós Fundador"],
                "open_review_count": 1,
            },
            {
                "slug": "clinic-c",
                "clinic_name": "Clinic C",
                "city": "Valencia",
                "status": "published",
                "specialist_claims": 1,
                "specialist_examples": ["Dra. Ana Tres"],
                "open_review_count": 3,
            }
        ],
        "covered_specialists": [
            {
                "slug": "clinic-b",
                "clinic_name": "Clinic B",
                "city": "Barcelona",
                "status": "preliminary",
                "specialist_entries": 5,
                "specialist_claims": 0,
                "specialist_examples": [],
                "open_review_count": 0,
            }
        ],
    }
    output = format_coverage(report)

    check(pct(1, 4) == "25%", "percentage formatting missing")
    check("# Vitalarga specialist coverage" in output, "title missing")
    check("Clínicas visibles: 4" in output, "visible clinic count missing")
    check("Con especialistas publicados: 1 (25%)" in output, "covered percentage missing")
    check("Sin especialistas publicados: 3 (75%)" in output, "missing percentage missing")
    check("Entradas de especialistas publicadas: 5" in output, "specialist entry count missing")
    check("Clínicas con nombres internos de especialistas: 2" in output, "claim coverage missing")
    check("Clínicas con revisión abierta sobre especialistas: 1" in output, "review coverage missing")
    check(prioritized_missing_rows(report)[0]["clinic_name"] == "Clinic C", "missing rows should prioritize open reviews")
    check(next_specialist_action(report) == "Revisar Clinic C: ya tiene 3 revisiones abiertas.", "next specialist action missing")
    check("Siguiente acción: Revisar Clinic C: ya tiene 3 revisiones abiertas." in output, "next specialist action line missing")
    check("Writes data: no" in output, "read-only signal missing")
    check(clean_specialist_example("Dr. Ibanez Sesion") == "", "session/navigation fragments should not become specialists")
    check(clean_specialist_example("Dr. Joan Josep Fuertes Medicina") == "Dr. Joan Josep Fuertes", "medical role should be trimmed after full name")
    check(clean_specialist_example("Alergología Anestesiología") == "", "specialty lists should not become specialist examples")
    check(clean_specialist_example("Neurocirugía Neurología Obstetricia Oftalmología") == "", "long specialty menus should be ignored")
    check(clean_specialist_example("Dra. Anna Paola Medicina Estética") == "Dra. Anna Paola", "role words should stop after the person name")
    noisy_line = format_clinic_line({
        "clinic_name": "Olympia",
        "city": "Madrid",
        "status": "preliminary",
        "specialist_claims": 2,
        "specialist_examples": ["Alergología Anestesiología", "Neurocirugía Neurología Obstetricia Oftalmología"],
        "open_review_count": 1,
    })
    check("2 señales internas sin nombre claro" in noisy_line, "noisy specialist signals should be labeled clearly")
    check(specialist_examples(report["missing_specialists"][0]) == ["Dra. Maria Uno", "Dr. Luis Dos"], "specialist examples missing")
    check("Clinic A · Madrid · publicada · 2 nombres detectados · ej.: Dra. Maria Uno, Dr. Luis Dos · 1 revisión abierta" in output, "missing clinic line missing")
    check(output.index("Clinic C") < output.index("Clinic A"), "higher-review missing clinic should be listed first")
    check("Clinic B · Barcelona · preliminar · 5 especialistas" in output, "covered clinic line missing")
    print("OK specialist coverage: report is read-only")


if __name__ == "__main__":
    main()
