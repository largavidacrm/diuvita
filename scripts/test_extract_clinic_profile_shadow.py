#!/usr/bin/env python3
"""Basic checks for the shadow clinic profile extractor."""
from capture_source_snapshot import FetchResult
from extract_clinic_profile_shadow import extract_from_fetch


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = """
<!doctype html>
<html>
<head><title>Example Longevity Clinic | Barcelona</title></head>
<body>
  <h1>Example Longevity Clinic</h1>
  <p>Medicina preventiva, longevidad, nutrición y medicina del sueño.</p>
  <p>Unidad de Longevidad dirigida por Dra. Laura García Pérez.</p>
  <p>Pruebas disponibles: DEXA, VO2 max, biomarcadores y test epigenético.</p>
  <p>Contacto: info@exampleclinic.test +34 930 111 222 @exampleclinic</p>
</body>
</html>
""".encode("utf-8")
    extraction = extract_from_fetch(
        FetchResult(
            source_url="https://exampleclinic.test/longevidad",
            final_url="https://exampleclinic.test/longevidad",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=html,
        )
    )
    profile = extraction["candidate_profile"]
    fields = {claim["field_path"]: claim for claim in extraction["field_claims"]}
    check(profile["name"] == "Example Longevity Clinic", "name guess failed")
    check(profile["emails"] == ["info@exampleclinic.test"], "email extraction failed")
    check(profile["instagram"] == ["@exampleclinic"], "instagram extraction failed")
    check("VO2 max" in profile["technologies"], "technology detection failed")
    check("Medicina preventiva" in profile["services"], "service detection failed")
    check("Unidad de Longevidad" in profile["units"], "unit detection failed")
    check("Dra. Laura García Pérez" in profile["professionals"], "professional detection failed")
    check("contact.email" in fields, "email claim missing")
    check("units.list" in fields, "unit claim missing")
    check("professionals.published" in fields, "professional claim missing")
    check(extraction["rule_decisions"], "rule decisions missing")
    print("OK extraction: shadow clinic profile")


if __name__ == "__main__":
    main()
