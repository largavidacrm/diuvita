#!/usr/bin/env python3
"""Checks that the admin dashboard shows auto-publication maturity blockers."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function loadClaimQuality",
        "function adminReadinessBlockers",
        '.from("field_claims")',
        '.select("field_path, verification_status, source_record_id, confidence, agent_name")',
        "function isNoisyTitleIdentityClaim",
        "Madurez auto-publicación",
        "Motivo principal",
        "Lista para Daniel",
        "muestra humana",
        "claims en conflicto",
        "claims rechazados",
        "claims sin fuente",
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache);",
    ]:
        check(marker in index, f"missing admin maturity marker: {marker}")

    check(
        "var claimQuality = await loadClaimQuality();" in index,
        "dashboard should load claim quality before rendering system status",
    )
    print("OK admin maturity: readiness blockers visible")


if __name__ == "__main__":
    main()
