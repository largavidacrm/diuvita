#!/usr/bin/env python3
"""Checks that the admin dashboard shows repeated enrichment-card pressure."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        'id="relatedReviewsPanel"',
        'id="relatedReviewPlan"',
        'id="relatedReviewsList"',
        "function reviewBacklogQuality",
        "function reviewBacklogGuardStatus",
        "function duplicateBacklogTargetLabel",
        "function enrichmentReviewGroups",
        "function duplicateEnrichmentGroups",
        "function firstDuplicateReview",
        "function clinicReviewWorkgroups",
        "function firstClinicWorkgroup",
        "function clinicWorkgroupSubject",
        "function clinicWorkgroupLabel",
        "function activeClinicWorkgroup",
        "function reviewMatchesClinicGroup",
        "function openClinicWorkgroup",
        "function duplicateEnrichmentClinicIds",
        "function isDuplicateEnrichmentReview",
        "function relatedOpenReviews",
        "function reviewWorkgroupRank",
        "function sortReviewWorkgroup",
        "function clinicReviewBundle",
        "function reviewWorkgroupRecommendation",
        "function renderRelatedReviewPlan",
        "function renderRelatedReviews",
        "function reviewTypeCell",
        "duplicateClinics",
        "duplicateReviews",
        "reviewDuplicateFilter",
        "data-review-duplicate",
        "data-related-review-id",
        "Otras revisiones de esta clínica",
        "tarjetas abiertas en este grupo",
        "Orden recomendado",
        "Atascos",
        "Varias propuestas",
        "Duplicados mejoras",
        "Tarjetas duplicadas",
        "Primer atasco",
        "Grupo por clínica",
        'id="openClinicGroupBtn"',
        "Filtrar grupo",
        "Grupo",
        'id="openDuplicateReviewBtn"',
        "Abrir atasco",
        "firstDuplicateTarget",
        "Freno bandeja",
        "SAFE_WRITE_REVIEW_BACKLOG_LIMIT",
        "Cerca · ",
        "Activo · ",
        "Sin duplicados",
    ]:
        check(marker in index, f"missing admin review backlog marker: {marker}")

    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    for marker in [
        ".related-reviews",
        ".related-review-plan",
        ".related-review-counts",
        ".related-review-list",
        ".related-review-item",
    ]:
        check(marker in css, f"missing related review style: {marker}")

    print("OK admin review backlog: duplicate pressure visible")


if __name__ == "__main__":
    main()
