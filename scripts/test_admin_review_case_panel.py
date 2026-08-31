#!/usr/bin/env python3
"""Checks that the admin review inbox exposes a clinic case work panel."""
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
        "Caso recomendado",
        "Caso en curso",
        "Trabajar caso",
        "Abrir primera tarjeta",
        "Ver toda la bandeja",
        "Revisa este grupo como una unidad",
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

    for marker in [
        ".review-case-panel",
        ".review-case-lead",
        ".review-case-meta",
        ".review-case-actions",
        ".review-case-meta .pill.wide",
    ]:
        check(marker in css, f"missing review case panel style: {marker}")

    print("OK admin review case panel: clinic workgroups are visible")


if __name__ == "__main__":
    main()
