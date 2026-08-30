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
        "function syncReviewFiltersFromInputs",
        "function filteredReviewRows",
        'id="globalPlanPanel"',
        'id="globalPlanFocus"',
        'id="globalPlanWhy"',
        'id="globalPlanNextAction"',
        'id="globalPlanOpenNextBtn"',
        'id="globalPlanRoadmap"',
        "globalPlanNextReviewId",
        "globalPlanNextGroupId",
        "function globalPlanLane",
        "function globalPlanFocusCopy",
        "function globalPlanBottleneckText",
        "function globalPlanNextDetailText",
        "function globalPlanCodexWorkDetail",
        "function globalPlanNowDetail",
        "function locationPlanLabel",
        "globalPlanNowDetail(openCount, backlogGuard, nextClick, bottleneck)",
        "locationPlanLabel(completeness)",
        "No crees trabajos nuevos.",
        "Freno de bandeja",
        "function countOpenReviewsByType",
        "function openGlobalPlanNext",
        "function googleLinkReviewRows",
        "function firstGoogleLinkReview",
        "function openGoogleLinksTarget",
        'id="openPriorityReviewBtn"',
        'id="openGoogleLinksBtn"',
        "Abrir siguiente",
        "Abrir prioridad",
        "Abrir Google Maps",
        "Plan global",
        "Estamos aquí",
        "Tu próximo clic",
        "Lo esencial: estado actual, tu próximo clic y lo que queda después.",
        "Estamos en control interno.",
        "Tú ahora",
        "Yo puedo seguir con",
        "Datos pendientes",
        "No activar todavía",
        "Validación final",
        "Autonomía / Growth",
        "Mapa simple del plan",
        "Base técnica",
        "Control interno",
        "Fuentes verificables",
        "Candidatas nuevas",
        "Fichas completas",
        "Autonomía",
        "Growth",
        "Filtrar grupo",
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
        "var nextReview = firstActionReview(rows, 0);",
        "var nextReview = firstActionReview(filteredReviewRows(), 0);",
        'el("openGoogleLinksBtn").addEventListener("click", openGoogleLinksTarget);',
    ]:
        check(marker in index, f"missing next-action marker: {marker}")

    check("global-plan-step" not in index, "global plan should not render decorative step numbers")

    print("OK admin next action: review priority visible")


if __name__ == "__main__":
    main()
