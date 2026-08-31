#!/usr/bin/env python3
"""Checks the per-clinic publication readiness formatter."""
from clinic_publication_readiness import (
    compact_lookup_key,
    format_readiness,
    missing_fix_hints,
    missing_required_fields,
    next_publication_step,
    readiness_summary,
    sort_matches,
    visibility_message,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    check(compact_lookup_key("Rose Bar") == "rosebar", "lookup key should remove spaces")
    check(compact_lookup_key("Clínica Benzaquén") == "clinicabenzaquen", "lookup key should remove accents")

    draft = {
        "slug": "rose-bar-longevity",
        "clinic_name": "Rose Bar Longevity",
        "city": "Madrid",
        "country": "Espana",
        "status": "draft",
        "has_name": True,
        "has_city": True,
        "has_country": True,
        "has_website": True,
        "has_address": False,
        "has_summary": False,
        "has_services": True,
        "has_google_maps": False,
        "open_reviews": 2,
        "open_blocking_reviews": 1,
        "updated_at": "2026-08-31T07:30:00+00:00",
    }
    missing = missing_required_fields(draft)
    check("Direccion o sede" in missing, "missing address should be reported")
    check("Resumen suficiente" in missing, "short summary should be reported")
    check("Google Maps de clinica" in missing, "missing direct Maps profile should be reported")
    check("Claims bloqueantes" in missing, "blocking reviews should be reported")
    hints = dict(missing_fix_hints(missing))
    check("perfil real de la clinica" in hints["Google Maps de clinica"], "Maps fix hint should reject generic links")
    check("bandeja de revision" in hints["Claims bloqueantes"], "blocking fix hint should point to review queue")
    check("No visible" in visibility_message(draft), "draft visibility should be explicit")
    check(
        next_publication_step(draft, missing).startswith("Completar primero: Direccion o sede"),
        "next step should point to the first missing field",
    )

    complete = dict(draft)
    complete.update({
        "status": "published",
        "has_address": True,
        "has_summary": True,
        "has_google_maps": True,
        "open_blocking_reviews": 0,
    })
    check(not missing_required_fields(complete), "complete profile should have no required blockers")
    check("Visible en la web" in visibility_message(complete), "published visibility should be explicit")
    check("si no ves cambios online" in next_publication_step(complete, []), "published complete next step should mention public freshness")

    output = format_readiness({
        "query": "rose",
        "matches": [draft],
        "summary": readiness_summary([draft]),
        "generated_at": "2026-08-31T07:31:00+00:00",
    })
    check("Rose Bar Longevity" in output, "clinic name should be shown")
    check("Clínicas medidas: 1" in output, "summary count should be shown")
    check("Mostradas: 1" in output, "shown count should be displayed")
    check("Con faltantes: 1" in output, "missing summary should be shown")
    check("Faltantes principales: Claims bloqueantes: 1" in output, "top missing summary should be shown")
    check("Falta para publicar:" in output, "publication blockers line should be shown")
    check("Donde corregirlo:" in output, "field-level fix hints should be shown")
    check("Google Maps de clinica: campo Google Maps; pega el perfil real de la clinica" in output, "Maps fix should be explicit")
    check("Siguiente paso: Completar primero: Direccion o sede" in output, "next publication step should be shown")
    check("Writes data: no" in output, "read-only guarantee should be shown")

    global_rows = [
        dict(complete, slug="complete-clinic", clinic_name="Complete Clinic"),
        draft,
        dict(draft, slug="missing-summary", clinic_name="Missing Summary", has_address=True, has_google_maps=True, open_blocking_reviews=0),
    ]
    sorted_rows = sort_matches(global_rows)
    check(sorted_rows[0]["slug"] == "rose-bar-longevity", "global mode should show most blocked clinics first")
    summary = readiness_summary(global_rows)
    check(summary["clinics_measured"] == 3, "global summary should count measured clinics")
    check(summary["ready_clinics"] == 1, "global summary should count ready clinics")
    check(summary["clinics_with_missing_fields"] == 2, "global summary should count blocked clinics")
    global_output = format_readiness({
        "query": "",
        "matches": sorted_rows,
        "summary": summary,
        "generated_at": "2026-08-31T07:31:00+00:00",
    })
    check("Consulta: todas las fichas no archivadas" in global_output, "global query label should be clear")
    check("Mostrando 3 fichas prioritarias por faltantes" in global_output, "global multi-match label should be clear")
    check("Sin faltantes obligatorios: 1" in global_output, "global ready count should be shown")
    check("Mostradas: 3" in global_output, "global shown count should be displayed")
    check(global_output.find("## Rose Bar Longevity") < global_output.find("## Missing Summary"), "most blocked clinic should appear first")

    empty = format_readiness({"query": "missing", "matches": [], "summary": readiness_summary([]), "generated_at": "2026-08-31T07:31:00+00:00"})
    check("No he encontrado una clinica" in empty, "empty result should be clear")

    print("OK clinic publication readiness: formatter is explicit")


if __name__ == "__main__":
    main()
