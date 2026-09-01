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
        "function reviewStableTieBreak",
        "function firstClinicClaimRequestReview",
        "function syncReviewFiltersFromInputs",
        "function filteredReviewRows",
        'id="globalPlanPanel"',
        'id="globalPlanFocus"',
        'id="globalPlanWhy"',
        'id="globalPlanNextAction"',
        'id="globalPlanOpenNextBtn"',
        'id="globalPlanCheckpoints"',
        'id="globalPlanRoadmap"',
        'class="global-plan-details"',
        "Ver desglose del plan",
        "globalPlanNextReviewId",
        "globalPlanNextGroupId",
        "function globalPlanRoleCard",
        "function globalPlanLane",
        "function globalPlanCheckpoint",
        "function globalPlanFocusCopy",
        "function globalPlanBottleneckText",
        "function globalPlanNextDetailText",
        "function globalPlanCodexWorkDetail",
        "Consolidar especialistas ya propuestos en tarjetas abiertas, sin publicarlos automáticamente.",
        "Convertir nombres internos de especialistas en propuestas revisables.",
        "function reviewBacklogNeedsCare",
        "safeWriteReviewSlots(openCount) <= 3",
        "function globalPlanNowDetail",
        "function globalPlanBlockerLabel",
        "function globalPlanBlockerDetail",
        "function globalPlanAfterText",
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
        'id="reviewActionTitle"',
        'id="reviewActionDetail"',
        "function reviewActionLeadCopy",
        "Qué hacer ahora",
        "Abrir prioridad: ",
        "Filtrar grupo",
        "Acepta solo el perfil real de la clínica",
        "Abrir siguiente",
        "Abrir prioridad",
        "Abrir Google Maps",
        "Plan global",
        "Estamos aquí",
        "Tu próximo clic",
        "Ahora",
        "Bloqueo",
        "Después",
        "Bandeja casi llena",
        "Después de bajar bandeja",
        "Primero mira tu próximo clic. Lo demás es contexto.",
        "Estamos bajando la bandeja antes de crear más trabajo.",
        "Ruta: Filtrar grupo · Abrir una propuesta · Aprobar, rechazar o modificar · Siguiente automática.",
        "Tu foco",
        "Trabajo Codex",
        "Mejoras seguras",
        "Parado",
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
        "data-review-group",
        "Siguiente acción",
        "Caso prioritario",
        "Contexto de grupo",
        "Fichas pendientes",
        "Revisar claim bloqueante",
        "Revisar reclamación",
        "Abrir reclamación",
        "Abre la reclamación, revisa quién la solicita",
        "Validar candidatas",
        "Revisar cambios de fuente",
        "Mejorar fichas existentes",
        "Revisión manual de fichas",
        "Sin acción urgente",
        "renderGlobalPlanStatus(summary, claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache);",
        "renderSystemStatus(summary, jobRows.data || [], eventRows.data || [], claimQuality, sourceMonitoring, sourceCoverage, specialistCoverage, profileCompleteness, publicHealth, publicationControl, reviewCache, publicationReadiness);",
        "var nextReview = firstActionReview(rows, 0);",
        "var nextReview = firstActionReview(filteredReviewRows(), 0);",
        '.order("title", { ascending: true })',
        '.order("id", { ascending: true })',
        'el("openGoogleLinksBtn").addEventListener("click", openGoogleLinksTarget);',
    ]:
        check(marker in index, f"missing next-action marker: {marker}")

    check("global-plan-step" not in index, "global plan should not render decorative step numbers")
    check('"Prioridad · "' not in index, "quick-action buttons should not carry long dynamic labels")
    check('"Maps · "' not in index, "Google Maps quick action should stay compact")
    check('systemItem("Grupo por clínica"' not in index, "clinic groups should be secondary context")
    check('systemItem("Siguiente ficha"' not in index, "profile queue should not name secondary clinics as the next action")

    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    for marker in [
        ".global-plan-checkpoints",
        ".global-plan-checkpoint",
        ".global-plan-checkpoint.is-active",
        ".global-plan-details summary",
        ".global-plan-details[open]",
        ".review-action-lead",
        ".review-action-buttons",
    ]:
        check(marker in css, f"missing global plan checkpoint style: {marker}")

    print("OK admin next action: review priority visible")


if __name__ == "__main__":
    main()
