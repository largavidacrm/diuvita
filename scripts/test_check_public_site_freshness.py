#!/usr/bin/env python3
"""Checks for the public-site freshness comparator."""

import check_public_site_freshness as freshness
from check_public_site_freshness import (
    check_clinic,
    clean_base_url,
    clinic_matches_query,
    compact_lookup_key,
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
        "city": "Barcelona",
        "country": "España",
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
    check(compact_lookup_key("Rose Bar") == "rosebar", "lookup key should remove spaces")
    check(compact_lookup_key("Clínica Benzaquén") == "clinicabenzaquen", "lookup key should remove accents")
    check(marker_present("Tel. 930 49 03 00", {"value": "+34 930 490 300", "mode": "digits"}), "phone marker should be spacing tolerant")
    check(clinic_matches_query(clinic, "Monarka"), "normal clinic names should match freshness checks")
    check(clinic_matches_query(clinic, "barcelona"), "clinic city should match freshness checks")
    check(not clinic_matches_query(clinic, "Rose Bar"), "unrelated clinic query should not match")
    check(clinic_matches_query({"name": "RoseBar Longevity Club"}, "Rose Bar"), "spaced query should match compact clinic names")
    check(fresh_result["fresh"] is True, "fresh page should have all public markers")
    check(old_result["fresh"] is False, "old page should miss new public markers")
    check(old_result["missing_markers"] > 0, "old page should report missing markers")
    check(len(old_result["missing_examples"]) == 4, "missing examples should respect the limit")

    original_load = freshness.load_public_clinics
    original_fetch = freshness.fetch_text
    try:
        freshness.load_public_clinics = lambda timeout, local_env: [clinic]
        freshness.fetch_text = lambda url, timeout: (200, old_html)
        report = run_freshness_check("https://example.test", timeout=3, slug="", missing_limit=2, clinic_query="Monarka")
    finally:
        freshness.load_public_clinics = original_load
        freshness.fetch_text = original_fetch

    output = format_report(report)
    check(report["writes_data"] is False, "freshness check must be read-only")
    check(report["clinic_query"] == "Monarka", "clinic query should be kept in the report")
    check(report["ok"] is False, "stale public page should fail freshness")
    check(report["stale_count"] == 1, "stale clinic should be counted")
    check("# Vitalarga public-site freshness" in output, "title missing")
    check("Consulta: Monarka" in output, "normal clinic query should be shown")
    check("Con desfase: 1" in output, "stale count missing")
    check("Monarka Clinic" in output, "clinic name missing")
    check("campos no aparecen" in output, "missing field summary missing")
    check("grupos:" in output, "missing field groups should be summarized")
    check("teléfono" in output, "missing phone group should be human-readable")
    check("especialistas" in output, "missing specialist group should be human-readable")
    check("Motivo probable: Supabase tiene datos que la web publicada todavía no ha incorporado" in output, "stale reason should be explained plainly")
    print("OK public-site freshness: stale published pages are detected")


if __name__ == "__main__":
    main()
