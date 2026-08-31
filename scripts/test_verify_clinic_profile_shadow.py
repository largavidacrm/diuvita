#!/usr/bin/env python3
"""Basic checks for the shadow claim verifier."""
from capture_source_snapshot import FetchResult
from extract_clinic_profile_shadow import extract_from_fetch
from verify_clinic_profile_shadow import verify_extraction


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = """
<!doctype html>
<html>
<head><title>Example Longevity Clinic | Barcelona</title></head>
<body>
  <p>Example Longevity Clinic offers medicina preventiva and VO2 max.</p>
  <p>La Unidad de Longevidad está dirigida por Dra. Laura García Pérez, nº colegiada 12345.</p>
  <p>Equipo de 12 especialistas con más de 20 años de experiencia.</p>
  <p>Consulta inicial: 120 euros.</p>
  <p>Sedes: Calle Serrano 100, 28006 Madrid.</p>
  <p>Email info@exampleclinic.test and phone +34 930 111 222 y 600 111 222.</p>
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
    extraction["field_claims"].append({
        "field_path": "contact.email",
        "value": "wrong@exampleclinic.test",
        "confidence": 0.88,
        "source_count": 1,
        "verifier_verdict": "unknown",
    })
    result = verify_extraction(extraction)
    verdicts = {
        (claim["field_path"], str(claim.get("value"))): claim["verifier_verdict"]
        for claim in result["verified_claims"]
    }
    check(result["summary"]["claims"] >= 4, "expected verified claims")
    check(verdicts[("contact.website", "https://exampleclinic.test")] == "accepted", "website should verify")
    check(verdicts[("contact.email", "info@exampleclinic.test")] == "accepted", "email should verify")
    check(verdicts[("contact.phone", "+34 930 111 222")] == "accepted", "primary phone should verify")
    check(verdicts[("contact.phone_mobile", "600 111 222")] == "accepted", "additional mobile phone should verify")
    check(verdicts[("professionals.published", "['Dra. Laura García Pérez']")] == "accepted", "professional should verify")
    check(verdicts[("transparency.years_in_practice", "más de 20 años")] == "accepted", "years claim should verify")
    check(verdicts[("transparency.specialists_count", "12")] == "accepted", "specialist-count claim should verify")
    check(verdicts[("team.credentialing_visible", "si")] == "accepted", "credentialing signal should verify")
    check(verdicts[("prices.public_status", "si")] == "accepted", "public-pricing signal should verify")
    check(
        any(claim["field_path"] == "location.locations" and claim["verifier_verdict"] == "accepted" for claim in result["verified_claims"]),
        "location claim should verify when address is explicit",
    )
    check(verdicts[("contact.email", "wrong@exampleclinic.test")] == "rejected", "wrong email should reject")
    check(result["summary"]["actions"].get("review", 0) >= 1, "auto-publish off should keep review actions")
    print("OK verification: shadow clinic claims")


if __name__ == "__main__":
    main()
