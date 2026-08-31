#!/usr/bin/env python3
"""Checks that clinic case helpers remain available without crowding the inbox."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        'id="reviewCasePanel"',
        'id="reviewCaseEyebrow"',
        'id="reviewCaseTitle"',
        'id="reviewCaseDetail"',
        'id="reviewCaseMeta"',
        'id="openCaseGroupBtn"',
        'id="clearCaseGroupBtn"',
        "Caso interno",
        "Filtrar caso",
        "Ver toda la bandeja",
        "Filtra este grupo",
        "Orden sugerido",
        "function reviewWorkgroupTypeCounts",
        "function reviewWorkgroupOrderLabel",
        "function reviewWorkgroupDetail",
        "function reviewWorkgroupMetaHtml",
        "function renderReviewCasePanel",
        "function openVisibleClinicWorkgroup",
        "function clearClinicWorkgroup",
        "renderReviewCasePanel();",
        'el("openCaseGroupBtn").addEventListener("click", openVisibleClinicWorkgroup);',
        'el("clearCaseGroupBtn").addEventListener("click", clearClinicWorkgroup);',
    ]:
        check(marker in index, f"missing review case panel marker: {marker}")

    case_panel_body = index[index.index("function renderReviewCasePanel"):index.index("function renderSystemStatus")]
    check("Caso recomendado" not in index, "review case panel should not appear as a default recommendation")
    check("Grupo recomendado" not in index, "review filters should not push a default recommended group")
    check("recommendedGroup" not in index, "review inbox should not calculate a default recommended group")
    check("show(panel, false);" in case_panel_body, "review case panel should stay hidden in the inbox")
    check("show(panel, true);" not in case_panel_body, "review case panel should not render as a visible inbox card")

    for marker in [
        ".review-case-panel",
        ".review-case-lead",
        ".review-case-meta",
        ".review-case-actions",
        ".review-case-meta .pill.wide",
    ]:
        check(marker in css, f"missing review case panel style: {marker}")

    print("OK admin review case panel: clinic workgroups stay available without crowding the inbox")


if __name__ == "__main__":
    main()
