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
        'id="clinicPublicSync"',
        'id="clinicPublicSyncTitle"',
        'id="clinicPublicSyncDetail"',
        'id="clinicPublicRebuildBtn"',
        'id="clinicPublishReadiness"',
        'id="clinicPublishReadinessTitle"',
        'id="clinicPublishReadinessMeta"',
        'id="clinicPublishMissingList"',
        'id="clinicPublishFilter"',
        'id="reviewActionNote"',
        'id="reviewFlowPanel"',
        'id="reviewFlowMeta"',
        'id="reviewFlowSteps"',
        "function publicVisibilityText",
        "function isPublicClinicStatus",
        "function clinicHasPendingPublicChange",
        "function renderClinicPublicSync",
        "function hasUnsavedClinicFormChanges",
        "function renderPublishReadiness",
        "function focusPublishField",
        "function publicRequiredProfileFields",
        "function clinicPublicationMissingLabels",
        "function clinicPublishReadinessCell",
        "function clinicMatchesPublishFilter",
        "function updateClinicSaveButtonLabel",
        "function isBlockingClinicClaim",
        "function reviewActionNote",
        "function renderReviewFlow",
        "activeClinicBlockingClaimCount",
        "Sin claims bloqueantes pendientes",
        "La candidata no se publica directamente.",
        "Cambia Estado a preliminar o publicada.",
        "La web pública solo cambia desde el editor de clínica.",
        "Crear borrador y validar",
        "Primero crea un borrador interno",
        "La publicación se decide después en el editor, en Validación final.",
        "Guardar como publicada",
        "Guardar borrador",
        "Falta para publicar",
        "Para publicar",
        "Completa estos puntos o guarda la ficha como borrador/revisión interna.",
        "Cambios todavía no guardados.",
        "Guardada, pendiente de verse online.",
        "No es un problema de guardado: la última web pública es anterior a esta edición.",
        "Se verá en Vitalarga después de actualizar la web.",
        "No está publicada en la web.",
        "Última edición de esta ficha:",
        "última web pública:",
        "Dirección o sede",
        "Google Maps de clínica",
        "data-publish-field",
        "Sin faltantes obligatorios",
        "Con faltantes",
        "Visibles con pendientes",
        "No visibles",
        'el("clinicPublishFilter").addEventListener("change", renderClinics)',
        "no aparecerá en la web",
        "aparecerá en la web",
    ]:
        check(marker in index, f"missing publication-flow marker: {marker}")

    check("updateClinicSaveButtonLabel();" in index, "validation should refresh save button label")
    check(".publication-hint" in css, "publication hint style missing")
    check(".publication-hint.visible-target" in css, "public-target hint style missing")
    check(".clinic-public-sync" in css, "clinic public sync style missing")
    check(".clinic-public-sync.is-pending" in css, "clinic public sync pending style missing")
    check(".clinic-public-sync.is-muted" in css, "clinic public sync muted style missing")
    check(".publish-readiness" in css, "publish readiness style missing")
    check(".publish-missing-chip" in css, "publish missing chip style missing")
    check(".publish-cell" in css, "clinic publish cell style missing")
    check(".field-attention" in css, "field attention style missing")
    check(".review-action-note" in css, "review action note style missing")
    check(".review-flow" in css, "review flow style missing")
    check(".review-flow-steps" in css, "review flow steps style missing")
    check(".review-flow-step" in css, "review flow step style missing")
    print("OK admin publication flow: status consequences are visible")


if __name__ == "__main__":
    main()
