#!/usr/bin/env python3
"""Checks that the admin dashboard shows per-clinic source coverage."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function emptySourceCoverage",
        "function sourceCoverageTargetSort",
        "function sourceCoverageTargetLabel",
        "async function loadSourceCoverage",
        "var sourceCoverage = await loadSourceCoverage();",
        "Fuentes por ficha",
        "Fichas sin fuente",
        "Siguiente fuente",
        "withHydratedSources",
        "withoutSources",
        "needingSourceWork",
        "blockingClaims",
        '.from("source_records")',
        '.from("field_claims")',
        '.eq("entity_type", "clinic")',
    ]:
        check(marker in index, f"missing admin source coverage marker: {marker}")

    check(
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, reviewCache);"
        in index,
        "dashboard should render source coverage status",
    )
    print("OK admin source coverage: status visible")


if __name__ == "__main__":
    main()
