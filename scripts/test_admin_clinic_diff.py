#!/usr/bin/env python3
"""Checks that the admin clinic editor exposes a before/after diff."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        'id="clinicProposalTitle"',
        "function clinicFormFields",
        "function diffItemHtml",
        "function renderUnsavedChanges",
        "function comparableClinicFields",
        "function versionClinicField",
        "function restoreChangeLabels",
        "function restoreChangeText",
        "activeClinicVersions",
        "Cambiaría:",
        "Cambios sin guardar",
        "Guardado",
        "Formulario",
    ]:
        check(marker in index, f"missing clinic diff marker: {marker}")

    for marker in [
        ".proposal-preview",
        ".proposal-diff",
        ".diff-item",
        ".diff-cols",
        ".version-main small",
    ]:
        check(marker in css, f"missing clinic diff style: {marker}")

    check(
        "renderUnsavedChanges();" in index,
        "clinic validation updates should refresh unsaved changes",
    )
    print("OK admin clinic diff: before/after preview wired")


if __name__ == "__main__":
    main()
