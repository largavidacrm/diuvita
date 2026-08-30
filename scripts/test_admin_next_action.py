#!/usr/bin/env python3
"""Checks that the admin dashboard surfaces the next review action."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function nextActionLabel",
        "function globalPlanPhase",
        "function renderGlobalPlanStatus",
        "function reviewPrimarySubject",
        "function firstActionReview",
        'id="globalPlanPanel"',
        'id="globalPlanNextAction"',
        'id="openPriorityReviewBtn"',
        "Abrir prioridad",
        "Plan global",
        "Siguiente trabajo recomendado",
        "Publicación web",
        "Siguiente acción",
        "Caso prioritario",
        "Revisar claim bloqueante",
        "Validar candidatas",
        "Revisar cambios de fuente",
        "Mejorar fichas existentes",
        "Completar fichas",
        "Sin acción urgente",
        "renderGlobalPlanStatus(summary, claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache);",
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache);",
    ]:
        check(marker in index, f"missing next-action marker: {marker}")

    print("OK admin next action: review priority visible")


if __name__ == "__main__":
    main()
