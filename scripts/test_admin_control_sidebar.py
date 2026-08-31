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
        'class="control-sidebar"',
        'class="control-nav"',
        'data-control-jump="allControlSections"',
        'data-control-jump="globalPlanPanel"',
        'data-control-jump="systemPanel"',
        'data-control-jump="reviewWorkArea"',
        'data-control-jump="clinicsPanel"',
        'data-control-jump="jobsPanel"',
        'data-control-jump="eventsPanel"',
        'id="navPlanMeta"',
        'id="navSystemMeta"',
        'id="navReviewMeta"',
        'id="navClinicMeta"',
        'id="navJobMeta"',
        'id="navEventMeta"',
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
        "setControlSectionVisible(activeControlSection)",
        'document.querySelectorAll("[data-control-jump]")',
        'updateControlNav(',
        'jumpToControlSection("reviewWorkArea")',
    ]:
        check(marker in index, f"missing control sidebar marker: {marker}")

    for marker in [
        ".control-layout",
        ".control-sidebar",
        ".control-nav",
        ".control-nav-item",
        ".control-nav-item.active",
        ".control-section-hidden",
        "grid-template-columns: 190px minmax(0, 1fr)",
        "grid-auto-flow: column",
        "overflow-x: auto",
    ]:
        check(marker in css, f"missing control sidebar style: {marker}")

    print("OK admin control sidebar: navigation is manageable")


if __name__ == "__main__":
    main()
