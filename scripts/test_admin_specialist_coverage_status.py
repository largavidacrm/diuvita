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
        "function loadSpecialistCoverage",
        '.select("status, current_data")',
        '.in("status", ["published", "preliminary"])',
        "var specialistCoverage = await loadSpecialistCoverage();",
        "Especialistas",
        "Pendientes especialistas",
        "withSpecialists",
        "withoutSpecialists",
    ]:
        check(marker in index, f"missing admin specialist coverage marker: {marker}")

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, specialistCoverage, profileCompleteness, publicHealth, reviewCache);"
        in index,
        "dashboard should render specialist coverage status",
    )
    print("OK admin specialist coverage: status visible")


if __name__ == "__main__":
    main()
