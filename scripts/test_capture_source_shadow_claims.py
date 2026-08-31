#!/usr/bin/env python3
"""Checks for capturing verified claims from hydrated source records."""

from argparse import Namespace

import capture_source_shadow_claims as capture
from verify_clinic_profile_shadow import verify_extraction


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_source():
    return {
        "source_record_id": "11111111-1111-1111-1111-111111111111",
        "clinic_id": "22222222-2222-2222-2222-222222222222",
        "clinic_slug": "example-longevity",
        "clinic_name": "Example Longevity Clinic",
        "clinic_status": "published",
        "source_type": "official_location_page",
        "source_url": "https://exampleclinic.test/contacto",
        "source_title": "Contacto | Example Longevity Clinic",
        "content_hash": "abc123",
        "retrieved_at": "2026-08-30T20:00:00+00:00",
        "metadata": {"final_url": "https://exampleclinic.test/contacto", "text_sha256": "def456"},
        "raw_excerpt": (
            "Example Longevity Clinic. Medicina preventiva, VO2 max y Unidad de Longevidad. "
            "Dirección Calle Serrano 100, 28006 Madrid. "
            "Contacto info@exampleclinic.test +34 930 111 222. "
            "Más de 20 años de experiencia. "
            "Dra. Laura García Pérez nº colegiada 12345. "
            "Precio consulta 120 €."
        ),
    }


def main():
    source = sample_source()
    extraction = capture.extraction_from_source(source)
    claims = capture.claims_from_verification(verify_extraction(extraction))
    by_path = {claim["field_path"]: claim for claim in claims}

    check(extraction["source"]["content_sha256"] == "abc123", "source content hash should be preserved")
    check(by_path["contact.email"]["value"] == "info@exampleclinic.test", "email claim missing")
    check(by_path["location.locations"]["value"][0]["address"].startswith("Calle Serrano"), "location claim missing")
    check(by_path["transparency.years_in_practice"]["value"] == "más de 20 años", "practice-years claim missing")
    check(by_path["team.credentialing_visible"]["value"] == "si", "credentialing claim missing")
    check(by_path["prices.public_status"]["value"] == "si", "pricing claim missing")

    args = Namespace(apply=False)
    dry_run = capture.process_source(source, args, "admin@example.test", {})
    check(dry_run["status"] == "ready", "dry-run source should be ready")
    check("captured" not in dry_run, "dry run must not write data")
    check("contact.email" in dry_run["claim_fields"], "compact field list should include email")

    sql = capture.insert_claims_sql(source, claims, "admin@example.test")
    check("insert into public.field_claims" in sql, "field claims insert SQL missing")
    check("source_shadow_claims_captured_at" in sql, "source metadata audit marker missing")
    check("public.review_queue" not in sql, "claim capture must not create review cards")
    check("public.clinics" not in sql.split("insert into public.field_claims", 1)[1].lower(), "claim capture must not edit clinic profiles")

    original_run_psql = capture.run_psql
    calls = []

    def fake_run_psql(sql_text, _local_env):
        calls.append(sql_text)
        return "[]"

    try:
        capture.run_psql = fake_run_psql
        rows = capture.load_hydrated_sources(7, "example-longevity", None, False, {})
    finally:
        capture.run_psql = original_run_psql

    check(rows == [], "fake source loader should return no rows")
    check("not exists (select 1 from public.field_claims fc where fc.source_record_id = sr.id)" in calls[0], "already-claimed guard missing")
    check("sr.content_hash" in calls[0], "source hash should be selected")
    check("sr.raw_excerpt" in calls[0], "hydrated source excerpt should be selected")
    check("official_location_page" in calls[0], "location/team sources should be prioritized")

    compact = capture.compact_output(capture.summarize([dry_run], False))
    check("verification_summary" not in compact["items"][0], "compact output should omit large verifier summary")
    check(compact["items"][0]["claim_fields"], "compact output should keep claim fields")
    print("OK source shadow claim capture: hydrated sources can become internal field claims")


if __name__ == "__main__":
    main()
