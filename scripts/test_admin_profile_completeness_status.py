#!/usr/bin/env python3
"""Checks that the admin dashboard shows visible profile completeness."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function emptyProfileCompleteness",
        "function profileCompletenessFields",
        "function topPendingProfileField",
        "function profileNextTargetLabel",
        "function profilePendingFields",
        "function profileTargetSort",
        "function reviewMentionsProfileWork",
        "function loadProfileCompleteness",
        "var profileCompleteness = await loadProfileCompleteness(reviewCache);",
        "Fichas completas",
        "Fichas con pendientes",
        "Campo más pendiente",
        "Siguiente ficha",
        "withoutPendingFields",
        "withPendingFields",
        "pendingTechnology",
        "nextTarget: null",
        "openReviewCount",
        '.select("id, slug, display_name, city, status, website, address, summary, current_data")',
    ]:
        check(marker in index, f"missing admin profile completeness marker: {marker}")

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, specialistCoverage, profileCompleteness, publicHealth, reviewCache);"
        in index,
        "dashboard should render profile completeness status",
    )
    print("OK admin profile completeness: status visible")


if __name__ == "__main__":
    main()
