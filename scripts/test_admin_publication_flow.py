#!/usr/bin/env python3
"""Checks that the admin editor makes draft/public status consequences clear."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        'id="clinicPublicationHint"',
        'id="reviewActionNote"',
        "function publicVisibilityText",
        "function updateClinicSaveButtonLabel",
        "function reviewActionNote",
        "Crear borrador y validar",
        "Primero crea un borrador interno",
        "La publicación se decide después en el editor, en Validación final.",
        "Guardar como publicada",
        "Guardar borrador",
        "no aparecerá en la web",
        "aparecerá en la web",
    ]:
        check(marker in index, f"missing publication-flow marker: {marker}")

    check("updateClinicSaveButtonLabel();" in index, "validation should refresh save button label")
    check(".publication-hint" in css, "publication hint style missing")
    check(".publication-hint.visible-target" in css, "public-target hint style missing")
    check(".review-action-note" in css, "review action note style missing")
    print("OK admin publication flow: status consequences are visible")


if __name__ == "__main__":
    main()
