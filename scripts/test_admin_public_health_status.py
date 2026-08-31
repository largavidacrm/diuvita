#!/usr/bin/env python3
"""Checks that the admin dashboard shows public website health."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "PUBLIC_HEALTH_CHECKS",
        "function emptyPublicHealth",
        "function loadPublicHealth",
        "fetch(check.path",
        "Web pública",
        "Checks web",
        "var publicHealth = await loadPublicHealth();",
        "publicSite.ok + \"/\" + publicSite.checks + \" comprobaciones\"",
    ]:
        check(marker in index, f"missing admin public health marker: {marker}")

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache, publicationReadiness);"
        in index,
        "dashboard should render public health status",
    )
    print("OK admin public health: production status visible")


if __name__ == "__main__":
    main()
