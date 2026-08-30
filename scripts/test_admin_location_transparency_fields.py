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
        'id="clinicLocationEditor"',
        'id="clinicLocationRows"',
        'id="clinicAddLocationBtn"',
        'id="clinicLocations"',
        'id="clinicYearsInPractice"',
        'id="clinicSpecialistsCount"',
        'id="clinicTeamCredentialingVisible"',
        'id="clinicPublicPricing"',
        'id="clinicPricingUrl"',
        "function locationsToLines",
        "function linesToLocations",
        "function renderLocationEditor",
        "function readLocationEditorRows",
        "function currentClinicLocations",
        "function isGoogleMapsLikeUrl",
        "function googleMapsUrlHasPlaceSignal",
        "function googleMapsUrlNeedsManualReview",
        "function currentClinicMapsUrls",
        "function hasReviewedClinicMapsProfile",
        "function hasGenericClinicMapsCandidate",
        "function addClinicLocation",
        "function locationsHaveAddress",
        "setJsonLocations(currentData, \"locations\"",
        "setJsonInteger(currentData, \"specialists_count\"",
        "\"location.locations\": currentClinicLocations()",
        "\"location.maps_url\": trimmed(\"clinicMapsUrl\")",
        "\"location.google_reviews_url\": trimmed(\"clinicGoogleReviewsUrl\")",
        "\"transparency.years_in_practice\": trimmed(\"clinicYearsInPractice\")",
        "\"transparency.specialists_count\": trimmed(\"clinicSpecialistsCount\")",
        "\"team.credentialing_visible\": trimmed(\"clinicTeamCredentialingVisible\")",
        "\"prices.public_status\": trimmed(\"clinicPublicPricing\")",
        "\"prices.url\": trimmed(\"clinicPricingUrl\")",
        "Dirección o sede completa",
        "Google Maps de clínica, no dirección suelta",
        "/maps/search",
        "/maps/dir",
        "query_place_id=",
        "Transparencia revisada si existe en la web",
        "Añadir sede",
        "Quitar",
    ]:
        check(marker in index, f"missing admin location/transparency marker: {marker}")

    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    for marker in [
        ".location-editor",
        ".location-editor-head",
        ".location-row",
        ".location-row-grid",
    ]:
        check(marker in css, f"missing admin location editor style: {marker}")

    print("OK admin location transparency: fields wired")


if __name__ == "__main__":
    main()
