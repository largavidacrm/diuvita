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
        "function openGlobalPlanNext",
        "function duplicateEnrichmentClinicIds",
        "function isDuplicateEnrichmentReview",
        "function relatedOpenReviews",
        "function reviewWorkgroupRank",
        "function sortReviewWorkgroup",
        "function clinicReviewBundle",
        "function reviewWorkgroupRecommendation",
        "function enrichmentFieldKeys",
        "function relatedReviewSummaryItems",
        "function duplicateProposalFieldLabels",
        "function relatedReviewFieldsHtml",
        "function blockingClaimStatusLabel",
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
        "Revisa los campos solapados antes de guardar",
        "Campos repetidos",
        "Sin campos detallados en la propuesta",
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
        'id="jobBacklogHint"',
        "dashboardOpenReviewCount",
        "function updateJobBacklogHint",
        "Freno activo: limpia revisiones antes de crear más trabajos.",
        "Pausa preventiva: limpia revisiones antes de crear más trabajos.",
        "Freno de bandeja activo. Primero limpia revisiones.",
        "var paused = full || near",
        'el("jobBtn").disabled = paused',
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
        ".related-review-fields",
        ".job-backlog-hint",
        ".job-backlog-hint.warning",
        ".job-backlog-hint.danger",
    ]:
        check(marker in css, f"missing related review style: {marker}")

    print("OK admin review backlog: duplicate pressure visible")


if __name__ == "__main__":
    main()
