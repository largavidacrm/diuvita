#!/usr/bin/env python3
"""Checks that admin supports multi-location and transparency fields."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        'id="clinicMapsUrl"',
        'id="clinicGoogleReviewsUrl"',
        'id="clinicLocations"',
        'id="clinicYearsInPractice"',
        'id="clinicSpecialistsCount"',
        'id="clinicTeamCredentialingVisible"',
        'id="clinicPublicPricing"',
        'id="clinicPricingUrl"',
        "function locationsToLines",
        "function linesToLocations",
        "function locationsHaveAddress",
        "setJsonLocations(currentData, \"locations\"",
        "setJsonInteger(currentData, \"specialists_count\"",
        "\"location.locations\": linesToLocations",
        "\"location.maps_url\": trimmed(\"clinicMapsUrl\")",
        "\"location.google_reviews_url\": trimmed(\"clinicGoogleReviewsUrl\")",
        "\"transparency.years_in_practice\": trimmed(\"clinicYearsInPractice\")",
        "\"transparency.specialists_count\": trimmed(\"clinicSpecialistsCount\")",
        "\"team.credentialing_visible\": trimmed(\"clinicTeamCredentialingVisible\")",
        "\"prices.public_status\": trimmed(\"clinicPublicPricing\")",
        "\"prices.url\": trimmed(\"clinicPricingUrl\")",
        "Dirección o sede completa",
        "Dirección preparada para Google Maps",
        "Transparencia revisada si existe en la web",
    ]:
        check(marker in index, f"missing admin location/transparency marker: {marker}")

    print("OK admin location transparency: fields wired")


if __name__ == "__main__":
    main()
