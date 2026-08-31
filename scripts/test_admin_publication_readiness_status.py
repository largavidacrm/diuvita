#!/usr/bin/env python3
"""Checks that the admin dashboard summarizes publication readiness."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function emptyPublicationReadiness",
        "function publicationTargetSort",
        "function publicationReadinessSummary",
        "function publicationReadinessLabel",
        "function publicationMissingLabel",
        "function publicationTopMissingLabel",
        "function publicationNextTargetLabel",
        "publicationReadinessSummary(clinicCache)",
        "clinicPublicationMissingLabels(row)",
        "Listas para publicar",
        "Faltantes publicación",
        "Principal faltante",
        "Siguiente publicación",
        "Google Maps de clínica",
        "Claims bloqueantes",
        "Sin faltantes obligatorios",
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache, publicationReadiness);",
    ]:
        check(marker in index, f"missing publication readiness status marker: {marker}")

    check(
        "if (row.status === \"archived\") return;" in index,
        "archived clinics should be excluded from publication readiness",
    )
    check(
        "readiness.topMissingField = Object.keys(missingCounts).sort" in index,
        "top missing publication field should be computed",
    )
    print("OK admin publication readiness: status visible")


if __name__ == "__main__":
    main()
