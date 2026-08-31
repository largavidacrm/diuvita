#!/usr/bin/env python3
"""Checks that the admin dashboard shows published specialist coverage."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function emptySpecialistCoverage",
        "function countPublishedSpecialists",
        "function countSpecialistClaimNames",
        "function reviewMentionsSpecialists",
        "function specialistNextTargetLabel",
        "function specialistTargetSort",
        "function specialistTargetSubject",
        "function specialistTargetReviewRows",
        "function firstSpecialistTargetReview",
        "function openSpecialistTarget",
        "function loadSpecialistCoverage",
        "function reviewProfessionalsCount",
        "function reviewProfessionalsBadge",
        "reviewProfessionalsBadge(row)",
        "especialistas",
        "clinicPendingSpecialistsPanel",
        "Detectados en revisión interna",
        "function normalizedPersonKey",
        "function claimPersonValues",
        "function claimCanSuggestSpecialist",
        "function addClaimSpecialistSuggestions",
        "function pendingSpecialistsForClinic",
        "function renderPendingSpecialistsForClinic",
        "function addPendingSpecialistsToForm",
        "data-add-pending-specialists",
        "Cargar al formulario",
        "especialistas cargados. Revisa y guarda.",
        "renderUnsavedChanges();",
        "Están recogidos como propuesta",
        "Evidencia interna",
        "addClaimSpecialistSuggestions(publishedKeys, pendingByKey);",
        "clinicPendingSpecialistsPanel\").addEventListener",
        '.select("id, slug, display_name, city, status, current_data")',
        '.in("status", ["published", "preliminary"])',
        '.from("field_claims")',
        '.select("clinic_id, field_path, value, verification_status")',
        '.in("field_path", ["professionals.published", "team.public_professionals"])',
        "targetById[claim.clinic_id].specialistClaims += countSpecialistClaimNames(claim);",
        'target.specialistClaims === 1 ? " nombre detectado" : " nombres detectados"',
        "var specialistCoverage = await loadSpecialistCoverage(reviewCache);",
        "specialistCoverageCache = specialistCoverage;",
        "specialistCoverageCache && specialistCoverageCache.nextTarget",
        "openSpecialistTargetBtn",
        "specialist_review",
        "Filtrar especialistas",
        "Abrir especialistas",
        "Especialistas",
        "Pendientes especialistas",
        "Siguiente especialistas",
        "withSpecialists",
        "withoutSpecialists",
        "withSpecialistClaims",
        "withOpenSpecialistReviews",
        "nextTarget",
    ]:
        check(marker in index, f"missing admin specialist coverage marker: {marker}")

    specialist_body = index[
        index.index("function pendingSpecialistsForClinic"):
        index.index("function renderPendingSpecialistsForClinic")
    ]
    check(
        "addClaimLocationSuggestions" not in specialist_body,
        "specialist pending loader should not call location suggestions",
    )

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache);"
        in index,
        "dashboard should render specialist coverage status",
    )
    print("OK admin specialist coverage: status visible")


if __name__ == "__main__":
    main()
