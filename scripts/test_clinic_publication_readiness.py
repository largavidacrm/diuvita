#!/usr/bin/env python3
"""Checks the per-clinic publication readiness formatter."""
from clinic_publication_readiness import (
    format_readiness,
    missing_required_fields,
    visibility_message,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
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
    check("No visible" in visibility_message(draft), "draft visibility should be explicit")

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

    output = format_readiness({
        "query": "rose",
        "matches": [draft],
        "generated_at": "2026-08-31T07:31:00+00:00",
    })
    check("Rose Bar Longevity" in output, "clinic name should be shown")
    check("Falta para publicar:" in output, "publication blockers line should be shown")
    check("Writes data: no" in output, "read-only guarantee should be shown")

    empty = format_readiness({"query": "missing", "matches": [], "generated_at": "2026-08-31T07:31:00+00:00"})
    check("No he encontrado una clinica" in empty, "empty result should be clear")

    print("OK clinic publication readiness: formatter is explicit")


if __name__ == "__main__":
    main()
