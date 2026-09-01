#!/usr/bin/env python3
"""Checks that the admin review inbox quick filters are wired."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        'id="reviewFilterChips"',
        'id="reviewClearFilters"',
        'class="panel review-panel review-list-panel"',
        'class="review-toolbar"',
        'id="reviewActionStrip"',
        'class="filter-chip-group"',
        "REVIEW_TYPE_FILTERS",
        "REVIEW_PRIORITY_FILTERS",
        "function renderReviewFilterChips",
        "function reviewMatchesType",
        "function syncReviewFiltersFromInputs",
        "function filteredReviewRows",
        "function clearReviewFilters",
        "reviewProfessionalsCount(b) - reviewProfessionalsCount(a)",
        'value="blocking_claim_review"',
        '["blocking_claim_review", "Claims bloqueantes"]',
        'value="clinic_claim_request"',
        '["clinic_claim_request", "Reclamaciones"]',
        "data-review-type",
        "data-review-priority",
        "data-review-duplicate",
        "data-review-google-links",
        "data-review-specialists",
        "data-review-group",
        "data-review-group-clear",
        "reviewDuplicateFilter",
        "reviewGoogleLinksFilter",
        "reviewSpecialistsFilter",
        "reviewClinicGroupFilter",
        "function reviewHasGoogleLinkProposal",
        "function reviewGoogleMapsRowTriage",
        "function reviewGoogleMapsRowTriageLabel",
        "function reviewHasSpecialistProposal",
        "function reviewSpecialistSourceUrls",
        "function reviewRowDetail",
        "function reviewSubjectCell",
        "Abrirá: ",
        "No se publica solo.",
        "Fuente visible para revisar.",
        "Fuente pendiente: revisa la web oficial antes de cargar nombres.",
        "fuente visible",
        "fuente pendiente",
        "Google Maps propuesto. Acepta solo el perfil real de la clínica.",
        "Estado: \" + reviewGoogleMapsRowTriageLabel(row)",
        'if (item.kind === "maps_url") return Boolean(proposalLinkUrl(item.url));',
        'filterChip("Google Maps", googleLinkCount, reviewGoogleLinksFilter, { "data-review-google-links": "true" })',
        'filterChip("Especialistas", specialistCount, reviewSpecialistsFilter, { "data-review-specialists": "true" })',
        "[data-review-type],[data-review-priority],[data-review-duplicate],[data-review-google-links],[data-review-specialists],[data-review-group],[data-review-group-clear]",
    ]:
        check(marker in index, f"missing admin review filter marker: {marker}")

    for marker in [
        ".review-filter-panel",
        ".review-toolbar",
        ".review-action-strip",
        ".review-subject-cell",
        ".filter-chip-row",
        ".filter-chip-group",
        ".filter-chip",
        ".filter-chip.active",
    ]:
        check(marker in css, f"missing admin review filter style: {marker}")

    check(
        'el("reviewFilterChips").addEventListener("click"' in index,
        "quick filter clicks should be handled",
    )
    print("OK admin review filters: controls wired")


if __name__ == "__main__":
    main()
