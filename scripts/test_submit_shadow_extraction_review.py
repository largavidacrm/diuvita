#!/usr/bin/env python3
"""Basic checks for turning verified shadow extraction into a review payload."""
import inspect

from capture_source_snapshot import FetchResult
from extract_clinic_profile_shadow import extract_from_fetch
from submit_shadow_extraction_review import create_review, review_payload
from verify_clinic_profile_shadow import verify_extraction


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = """
<!doctype html>
<html>
<head><title>Example Longevity Clinic</title></head>
<body>
  <p>Medicina preventiva, longevidad and VO2 max.</p>
  <p>Unidad de Longevidad con Dra. Laura García Pérez, nº colegiada 12345.</p>
  <p>Equipo de 12 especialistas con más de 20 años de experiencia.</p>
  <p>Consulta inicial: 120 euros.</p>
  <p>Sede principal: Calle Serrano 100, 28006 Madrid.</p>
  <p>Teléfonos: 91 6325659 y 676 629 862.</p>
  <p>Contact: info@exampleclinic.test @exampleclinic</p>
</body>
</html>
""".encode("utf-8")
    extraction = extract_from_fetch(
        FetchResult(
            source_url="https://exampleclinic.test/longevity",
            final_url="https://exampleclinic.test/longevity",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=html,
        )
    )
    payload = review_payload("example-clinic", verify_extraction(extraction))
    fields = payload["proposed_fields"]
    check(payload["mode"] == "shadow", "payload should be shadow mode")
    check(payload["clinic_slug"] == "example-clinic", "clinic slug missing")
    check(fields["email"] == "info@exampleclinic.test", "email field missing")
    check(fields["telefono"] == "91 6325659", "primary phone field missing")
    check(fields["phone_mobile"] == "676 629 862", "mobile phone field missing")
    check(fields["instagram"] == "@exampleclinic", "instagram field missing")
    check(fields["locations"][0]["address"].startswith("Calle Serrano"), "location field missing")
    check(fields["unidades"] == ["Unidad de Longevidad"], "units field missing")
    check(fields["profesionales"] == ["Dra. Laura García Pérez"], "professionals field missing")
    check(fields["years_in_practice"] == "más de 20 años", "years-in-practice field missing")
    check(fields["specialists_count"] == 12, "specialist-count field missing")
    check(fields["team_credentialing_visible"] == "si", "credentialing field missing")
    check(fields["public_pricing"] == "si", "public-pricing field missing")
    check("field_claims" in payload, "claims missing")
    check("rule_decisions" in payload, "rule decisions missing")
    signature = inspect.signature(create_review)
    check(signature.parameters["replace_existing"].default is False, "existing review replacement should be opt-in")
    check(
        signature.parameters["allow_multiple_open_clinic_reviews"].default is False,
        "multiple clinic review cards should be opt-in",
    )
    check(
        signature.parameters["replace_existing_clinic_review"].default is False,
        "same-clinic review refresh should be opt-in",
    )

    captured = {}

    def fake_run_psql(sql, local_env):
        captured["sql"] = sql
        return '[{"status": "existing_clinic", "id": "review-1", "title": "Open review"}]'

    original_run_psql = create_review.__globals__["run_psql"]
    try:
        create_review.__globals__["run_psql"] = fake_run_psql
        result = create_review("example-clinic", payload, "admin@example.test", {})
    finally:
        create_review.__globals__["run_psql"] = original_run_psql

    check(result["status"] == "existing_clinic", "same-clinic open review should be reported")
    sql = captured.get("sql", "")
    check("open_clinic_reviews as" in sql, "same-clinic duplicate guard missing")
    check("existing_clinic as" in sql, "same-clinic existing review CTE missing")
    check("updated_clinic as" in sql, "same-clinic refresh CTE missing")
    check(
        "and (false or not exists (select 1 from existing_clinic))" in sql,
        "new review should be blocked when another clinic review is open",
    )

    captured.clear()

    def fake_run_psql_updated_clinic(sql, local_env):
        captured["sql"] = sql
        return '[{"status": "updated_clinic", "id": "review-1", "title": "Open review"}]'

    original_run_psql = create_review.__globals__["run_psql"]
    try:
        create_review.__globals__["run_psql"] = fake_run_psql_updated_clinic
        result = create_review(
            "example-clinic",
            payload,
            "admin@example.test",
            {},
            replace_existing_clinic_review=True,
        )
    finally:
        create_review.__globals__["run_psql"] = original_run_psql

    check(result["status"] == "updated_clinic", "same-clinic refresh should update the existing card")
    sql = captured.get("sql", "")
    check("where true\n    and rq.id = existing_clinic.id" in sql, "same-clinic refresh should be opt-in true")
    check(
        "and not exists (select 1 from updated_clinic)" in sql,
        "insert should be blocked after refreshing an existing clinic card",
    )
    print("OK review payload: shadow extraction")


if __name__ == "__main__":
    main()
