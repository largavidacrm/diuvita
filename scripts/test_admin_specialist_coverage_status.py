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
        "function reviewMentionsSpecialists",
        "function specialistNextTargetLabel",
        "function specialistTargetSort",
        "function specialistTargetSubject",
        "function specialistTargetReviewRows",
        "function firstSpecialistTargetReview",
        "function openSpecialistTarget",
        "function loadSpecialistCoverage",
        '.select("id, slug, display_name, city, status, current_data")',
        '.in("status", ["published", "preliminary"])',
        '.from("field_claims")',
        '.in("field_path", ["professionals.published", "team.public_professionals"])',
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

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache);"
        in index,
        "dashboard should render specialist coverage status",
    )
    print("OK admin specialist coverage: status visible")


if __name__ == "__main__":
    main()
