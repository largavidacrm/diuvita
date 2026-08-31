#!/usr/bin/env python3
"""Checks for the public-site freshness comparator."""

import check_public_site_freshness as freshness
from check_public_site_freshness import (
    check_clinic,
    clean_base_url,
    format_report,
    marker_present,
    normalize_digits,
    run_freshness_check,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_clinic():
    return {
        "slug": "monarka-clinic",
        "name": "Monarka Clinic",
        "status": "publicada",
        "email": "info@monarkaclinic.com",
        "telefono": "+34 930 490 300",
        "instagram": "@monarkaclinic",
        "services": ["Neurolongevidad y medicina de precisión"],
        "specialties": ["Neurolongevidad"],
        "unidades": ["Programa de Longevidad"],
        "profesionales": ["Dra. Estela Lladó-Carbó — neurofisiología clínica"],
        "locations": [{"label": "Sede principal", "address": "Paseo de Gracia 130, 08008 Barcelona"}],
        "tech": "IHHT (hipoxia intermitente)\nEstudio de Metabolismo",
        "years_in_practice": "más de 5 años",
        "specialists_count": "20",
        "team_credentialing_visible": "Parcial",
        "public_pricing": "No consta",
    }


def main():
    clinic = sample_clinic()
    fresh_html = """
    Monarka Clinic info@monarkaclinic.com 930490300 @monarkaclinic
    Neurolongevidad y medicina de precisión Neurolongevidad Programa de Longevidad
    Dra. Estela Lladó-Carbó — neurofisiología clínica Sede principal
    Paseo de Gracia 130, 08008 Barcelona IHHT (hipoxia intermitente)
    Estudio de Metabolismo más de 5 años 20 Parcial No consta
    """
    old_html = """
    Monarka Clinic info@monarkaclinic.com Neurolongevidad
    Paseo de Gracia 130, 08008 Barcelona IHHT (hipoxia intermitente)
    """
    fresh_result = check_clinic(clinic, fresh_html, missing_limit=4)
    old_result = check_clinic(clinic, old_html, missing_limit=4)

    check(clean_base_url("https://example.test/") == "https://example.test", "base URL should be normalized")
    check(normalize_digits("+34 930 490 300") == "34930490300", "phone digits should normalize")
    check(marker_present("Tel. 930 49 03 00", {"value": "+34 930 490 300", "mode": "digits"}), "phone marker should be spacing tolerant")
    check(fresh_result["fresh"] is True, "fresh page should have all public markers")
    check(old_result["fresh"] is False, "old page should miss new public markers")
    check(old_result["missing_markers"] > 0, "old page should report missing markers")
    check(len(old_result["missing_examples"]) == 4, "missing examples should respect the limit")

    original_load = freshness.load_public_clinics
    original_fetch = freshness.fetch_text
    try:
        freshness.load_public_clinics = lambda timeout, local_env: [clinic]
        freshness.fetch_text = lambda url, timeout: (200, old_html)
        report = run_freshness_check("https://example.test", timeout=3, slug="monarka-clinic", missing_limit=2)
    finally:
        freshness.load_public_clinics = original_load
        freshness.fetch_text = original_fetch

    output = format_report(report)
    check(report["writes_data"] is False, "freshness check must be read-only")
    check(report["ok"] is False, "stale public page should fail freshness")
    check(report["stale_count"] == 1, "stale clinic should be counted")
    check("# Vitalarga public-site freshness" in output, "title missing")
    check("Con desfase: 1" in output, "stale count missing")
    check("Monarka Clinic" in output, "clinic name missing")
    check("campos no aparecen" in output, "missing field summary missing")
    print("OK public-site freshness: stale published pages are detected")


if __name__ == "__main__":
    main()
