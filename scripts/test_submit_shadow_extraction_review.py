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
  <p>Unidad de Longevidad con Dra. Laura García Pérez.</p>
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
    check(fields["instagram"] == "@exampleclinic", "instagram field missing")
    check(fields["unidades"] == ["Unidad de Longevidad"], "units field missing")
    check(fields["profesionales"] == ["Dra. Laura García Pérez"], "professionals field missing")
    check("field_claims" in payload, "claims missing")
    check("rule_decisions" in payload, "rule decisions missing")
    signature = inspect.signature(create_review)
    check(signature.parameters["replace_existing"].default is False, "existing review replacement should be opt-in")
    print("OK review payload: shadow extraction")


if __name__ == "__main__":
    main()
