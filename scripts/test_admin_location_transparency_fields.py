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
        'id="clinicMapsUrlWarning"',
        'id="clinicGoogleReviewsUrl"',
        'id="clinicLocationEditor"',
        'id="clinicLocationRows"',
        'id="clinicAddLocationBtn"',
        'id="clinicLocations"',
        'id="clinicPendingLocationsPanel"',
        'id="clinicPendingLocationsList"',
        'id="clinicPendingLocationsActions"',
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
        "function locationIdentityKey",
        "function currentLocationKeys",
        "function locationDisplayText",
        "function isGoogleMapsLikeUrl",
        "function googleMapsUrlHasPlaceSignal",
        "function googleMapsUrlNeedsManualReview",
        "function currentClinicMapsUrls",
        "function hasReviewedClinicMapsProfile",
        "function hasGenericClinicMapsCandidate",
        "function googleMapsReviewMessage",
        "function focusFirstGenericMapsCandidate",
        "function updateClinicMapsWarnings",
        "function reviewedMapsProfileValue",
        "function sanitizeLocationMaps",
        "function sanitizedLocationsForSave",
        "activeClinicClaims = []",
        "activeClinicClaimSources = {}",
        "function claimArrayValues",
        "function claimCanSuggestLocation",
        "function addClaimLocationSuggestions",
        'row.field_path !== "location.locations"',
        '.eq("field_path", "location.locations")',
        '["rejected", "stale", "conflict"]',
        "Evidencia interna",
        "propuesta o evidencia interna",
        "evidencia interna",
        "function addClinicLocation",
        "function proposalLocations",
        "function pendingLocationsForClinic",
        "function renderPendingLocationsForClinic",
        "function addPendingLocationsToForm",
        "addClaimLocationSuggestions(existingKeys, pendingByKey);",
        "function locationsHaveAddress",
        "Sedes detectadas en revisión interna",
        "Cargar sedes al formulario",
        "sedes cargadas. Revisa y guarda.",
        "data-add-pending-locations",
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
        "Pega el perfil de Google Business de la clínica",
        "Google Maps pendiente: pega el perfil real de la clínica",
        'validationItem("Google Maps de clínica, no dirección suelta", hasClinicMapsProfile && !hasGenericMapsCandidate, publicTarget || hasGenericMapsCandidate, "clinicMapsUrl")',
        "if (hasGenericClinicMapsCandidate())",
        "focusFirstGenericMapsCandidate();",
        "updateClinicMapsWarnings();",
        'setJsonText(currentData, "maps_url", reviewedMapsProfileValue(trimmed("clinicMapsUrl")))',
        'setJsonLocations(currentData, "locations", sanitizedLocationsForSave(currentClinicLocations()))',
        'if ((key === "maps_url" || key === "google_maps_url") && !reviewedMapsProfileValue(proposalListValue(fields[key]))) return;',
        "/maps/search",
        "/maps/dir",
        "query_place_id=",
        "Transparencia revisada si existe en la web",
        "Añadir sede",
        "Sede principal",
        "Sede adicional",
        "Quitar",
    ]:
        check(marker in index, f"missing admin location/transparency marker: {marker}")

    check("Sede ' + html(index + 1)" not in index, "location editor should avoid decorative location numbers")

    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    for marker in [
        ".location-editor",
        ".location-editor-head",
        ".location-row",
        ".location-row-grid",
        ".field-warning",
        ".location-field-warning",
    ]:
        check(marker in css, f"missing admin location editor style: {marker}")

    print("OK admin location transparency: fields wired")


if __name__ == "__main__":
    main()
