#!/usr/bin/env python3
"""Checks the combined clinic visibility diagnostic."""
from clinic_public_visibility_report import (
    first_dict,
    format_visibility_report,
    missing_field_groups,
    public_status,
    stale_freshness_check,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def published_clinic():
    return {
        "slug": "monarka-clinic",
        "clinic_name": "Monarka Clinic",
        "city": "Barcelona",
        "status": "published",
        "updated_at": "2026-08-31T06:47:00+00:00",
        "has_name": True,
        "has_city": True,
        "has_country": True,
        "has_website": True,
        "has_address": True,
        "has_summary": True,
        "has_services": True,
        "has_google_maps": False,
        "open_blocking_reviews": 0,
    }


def main():
    stale_report = {
        "query": "Monarka",
        "generated_at": "2026-08-31T08:30:00+00:00",
        "writes_data": False,
        "readiness": {"matches": [published_clinic()]},
        "freshness": {
            "checks": [
                {
                    "fresh": False,
                    "missing_markers": 4,
                    "missing_examples": [
                        {"field": "telefono", "value": "+34 930 490 300"},
                        {"field": "unidades", "value": "Programa de Longevidad"},
                        {"field": "profesionales", "value": "Dra. Ejemplo"},
                        {"field": "tech", "value": "Calorimetría indirecta"},
                    ],
                }
            ]
        },
    }
    output = format_visibility_report(stale_report)

    check(first_dict([{}, {"a": 1}]) == {}, "first dict should keep the first dictionary")
    check(public_status("published"), "published should be public")
    check(not public_status("draft"), "draft should not be public")
    check(stale_freshness_check(stale_report["freshness"])["missing_markers"] == 4, "stale check missing")
    check(missing_field_groups(stale_freshness_check(stale_report["freshness"])) == ["teléfono", "unidades", "especialistas", "tecnología"], "field grouping missing")
    check("# Vitalarga clinic visibility report" in output, "title missing")
    check("Está guardada en Supabase, pero la web visible va por detrás." in output, "stale explanation missing")
    check("Diferencia detectada: 4 campos guardados todavía no aparecen online." in output, "missing count missing")
    check("Campos afectados: teléfono, unidades, especialistas, tecnología." in output, "affected groups missing")
    check("actualizar la web pública solo cuando Daniel decida asumir ese rebuild de Netlify" in output, "Netlify decision wording missing")
    check("Falta: Google Maps de clinica." in output, "publication completeness blocker missing")
    check("Dra. Ejemplo" not in output, "visibility report should not dump professional names")

    draft = dict(published_clinic(), status="draft", has_address=False, has_summary=False)
    draft_output = format_visibility_report({
        "query": "Rose Bar",
        "generated_at": "2026-08-31T08:31:00+00:00",
        "readiness": {"matches": [draft]},
        "freshness": {"checks": []},
    })
    check("No aparece en la web pública porque está como borrador." in draft_output, "draft explanation missing")
    check("Completar primero: Direccion o sede" in draft_output, "draft next step missing")

    fresh = dict(published_clinic(), has_google_maps=True)
    fresh_output = format_visibility_report({
        "query": "Monarka",
        "generated_at": "2026-08-31T08:32:00+00:00",
        "readiness": {"matches": [fresh]},
        "freshness": {"checks": [{"fresh": True}]},
    })
    check("No detecto desfase en los campos públicos medidos." in fresh_output, "fresh explanation missing")
    check("no hay bloqueo obligatorio detectado" in fresh_output, "fresh next step missing")

    empty_output = format_visibility_report({
        "query": "Missing",
        "generated_at": "2026-08-31T08:33:00+00:00",
        "readiness": {"matches": []},
    })
    check("No he encontrado una clínica" in empty_output, "empty result missing")
    check("Writes data: no" in output, "read-only marker missing")
    check("no toca Netlify" in output, "no-Netlify note missing")
    print("OK clinic public visibility: stale public pages are explained clearly")


if __name__ == "__main__":
    main()
