#!/usr/bin/env python3
"""Checks that the admin center has a manageable control sidebar."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        'class="control-layout"',
        'id="sidebarToggleBtn"',
        'class="control-sidebar"',
        'class="control-nav"',
        'data-control-jump="allControlSections"',
        'data-control-jump="globalPlanPanel"',
        'data-control-jump="systemPanel"',
        'data-control-jump="reviewWorkArea"',
        'data-control-jump="clinicsPanel"',
        'data-control-jump="jobCreatePanel"',
        'data-control-jump="jobsPanel"',
        'data-control-jump="eventsPanel"',
        'id="navPlanMeta"',
        'id="navSystemMeta"',
        'id="navReviewMeta"',
        'id="navClinicMeta"',
        'id="navRecommendMeta"',
        'id="navJobMeta"',
        'id="navEventMeta"',
        'class="panel job-create-panel"',
        'id="localVersionPill"',
        "window.VITALARGA_LOCAL_VERSION",
        "function renderLocalVersionPill",
        "Local · ",
        "Local sin sello de versión",
        "showMissingLocalVersion",
        'id="jobCreatePanel"',
        'id="jobForm"',
        'id="jobExistingClinic"',
        'id="jobSourceUrl"',
        'id="jobRequestedField"',
        "Qué quieres revisar",
        'id="jobQueryLabel"',
        'id="jobQueryHint"',
        'id="jobSourceUrlHint"',
        '<textarea id="jobQuery"',
        "Texto para el agente",
        "Link oficial",
        "Recomendar clínica",
        "Completar clínica existente",
        "Añadir a trabajos",
        'source: "admin_recommend_clinic_form"',
        "operator_note",
        'id="pendingJobsBody"',
        'id="pendingJobCount"',
        "Trabajos pendientes",
        "function jobSelectedRequestInfo",
        "function jobNextStepText",
        "Link oficial aportado",
        "Texto libre",
        "Siguiente: queda esperando búsqueda real",
        "function createExistingClinicSourceJob",
        'ui_route: "sidebar_existing_clinic_source_job"',
        "source_job_version: \"2026-09-01.recommend-clinic-source\"",
        "allowed_output: \"review_queue_proposal_only\"",
        "Prioridad: todas",
        'id="reviewWorkArea"',
        'id="clinicsPanel"',
        'id="jobsPanel"',
        'id="eventsPanel"',
        "function setControlNavActive",
        "function setControlSectionVisible",
        "function jumpToControlSection",
        "function updateControlNav",
        "ALL_CONTROL_SECTIONS",
        "activeControlSection",
        "CONTROL_SECTION_IDS",
        "SIDEBAR_STORAGE_KEY",
        "function setSidebarCollapsed",
        "function toggleSidebar",
        'document.body.classList.toggle("sidebar-collapsed"',
        'window.localStorage.setItem(SIDEBAR_STORAGE_KEY',
        'el("sidebarToggleBtn").addEventListener("click", toggleSidebar)',
        "setControlSectionVisible(activeControlSection)",
        'document.querySelectorAll("[data-control-jump]")',
        'updateControlNav(',
        'jumpToControlSection("reviewWorkArea")',
    ]:
        check(marker in index, f"missing control sidebar marker: {marker}")

    for removed_marker in [
        'data-job-query=',
        'data-job-clinic=',
        'IMDA: dirección y contacto',
        'Regenera: especialistas',
        'RoseBar: ubicación',
        'Neleva: especialistas',
    ]:
        check(removed_marker not in index, f"old recommendation example should be gone: {removed_marker}")

    for marker in [
        ".control-layout",
        ".sidebar-toggle",
        "body.sidebar-collapsed .admin-main",
        "body.sidebar-collapsed .control-layout",
        "body.sidebar-collapsed .control-sidebar",
        ".control-sidebar",
        ".control-nav",
        ".control-nav-item",
        ".control-nav-item.active",
        ".local-version-pill",
        ".local-version-pill.warning",
        "max-width: min(34rem, 42vw)",
        ".control-section-hidden",
        "grid-template-columns: 260px minmax(0, 1fr)",
        "width: min(1680px, 96vw)",
        ".job-create-panel",
        ".job-form-grid",
        ".panel-subhead",
        "grid-auto-flow: column",
        "overflow-x: auto",
        "--text-label",
        "--text-ui",
        "--text-body",
        "--text-stat",
        "font-size: var(--text-ui)",
        "font-size: var(--text-body)",
        "font-size: var(--text-title-sm)",
        ".job-next-step",
    ]:
        check(marker in css, f"missing control sidebar style: {marker}")

    check(
        index.index('class="control-content"') < index.index('id="jobCreatePanel"') < index.index('id="jobsPanel"'),
        "recommendation form should live in the main dashboard content before pending jobs",
    )

    print("OK admin control sidebar: navigation is manageable")


if __name__ == "__main__":
    main()
