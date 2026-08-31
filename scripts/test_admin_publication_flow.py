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
        'id="clinicPhoneWarning"',
        'id="clinicPhoneFixedWarning"',
        'id="clinicPhoneMobileWarning"',
        'id="clinicPhoneWhatsappWarning"',
        'id="reviewDecisionSummary"',
        'id="reviewAffectedClinic"',
        'id="reviewProposalType"',
        'id="reviewCurrentRelevantPanel"',
        'id="reviewCurrentRelevantList"',
        'id="reviewProposalFocus"',
        'id="reviewProposalFocusTitle"',
        'id="reviewProposalFocusMeta"',
        'id="reviewProposalFocusCount"',
        'id="reviewProposalFocusList"',
        'id="reviewEvidencePanel"',
        'id="reviewEvidenceList"',
        'id="reviewWarningPanel"',
        'id="reviewModifyPanel"',
        'id="reviewApproveBtn"',
        'id="reviewRejectBtn"',
        'id="reviewModifyBtn"',
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
        "function renderReviewValidationView",
        "function approveExistingClinicReview",
        "function approvalSafetyWarnings",
        "function finishReviewDecision",
        "function spanishPhoneDigits",
        "function isPlausibleSpanishPhone",
        "function clinicPhoneReviewMessage",
        "function updateClinicPhoneWarnings",
        "function hasWeakClinicPhoneCandidate",
        "function focusFirstWeakClinicPhone",
        "activeClinicBlockingClaimCount",
        "Sin claims bloqueantes pendientes",
        "Teléfonos reales, no identificadores",
        "Teléfono pendiente: corrige o borra el campo marcado antes de guardar.",
        "No parece un teléfono español válido. Corrígelo o bórralo antes de guardar.",
        "No se publican datos automáticamente.",
        "Google Maps debe ser el perfil real de la clínica",
        "Duplicado probable: no apruebo una ficha nueva desde esta tarjeta.",
        "Guardar como publicada",
        "Guardar borrador",
        "Falta para publicar",
        "Abre la ficha y completa ese campo.",
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
        "Pendientes de web pública",
        "Pendiente de web",
        "Guardada en admin",
        "Guardada; pendiente de actualizar web pública.",
        "La web pública va por detrás; se verá tras la actualización agrupada.",
        "No visibles",
        'el("clinicPublishFilter").addEventListener("change", renderClinics)',
        'if (filter === "web_pending") return clinicHasPendingPublicChange(row, publicationControlCache);',
        "no aparecerá en la web",
        "aparecerá en la web",
        'id="reviewListPanel"',
        'id="reviewClinicPanel"',
        'id="reviewClinicProfileName"',
        'id="reviewClinicProfileData"',
        'id="reviewBackToListBtn"',
        'id="reviewSelectionPanel"',
        "Datos actuales relevantes",
        "Información nueva a valorar",
        "Fuente o evidencia",
        "Advertencias imprescindibles",
        "Aprobar",
        "Rechazar",
        "Modificar",
        "function renderReviewProposalFocus",
        "function renderReviewClinicPanel",
        "function reviewClinicProfileDataItems",
        "function reviewProposalFocusItems",
        "function renderReviewDecisionSummary",
        "function renderReviewCurrentRelevant",
        "function renderReviewEvidence",
        "function renderReviewWarnings",
        "function reviewClinicForRow",
        "function snapshotValueHtml",
        "show(el(\"reviewSelectionPanel\"), false)",
        "show(el(\"reviewListPanel\"), false)",
        "show(el(\"reviewClinicPanel\"), true)",
        "show(el(\"reviewSelectionPanel\"), true)",
    ]:
        check(marker in index, f"missing publication-flow marker: {marker}")

    check("updateClinicSaveButtonLabel();" in index, "validation should refresh save button label")
    check("if (hasWeakClinicPhoneCandidate())" in index, "save should block suspicious phone values")
    check("updateClinicPhoneWarnings();" in index, "validation should refresh phone warnings")
    check(".publication-hint" in css, "publication hint style missing")
    check(".publication-hint.visible-target" in css, "public-target hint style missing")
    check(".clinic-public-sync" in css, "clinic public sync style missing")
    check(".clinic-public-sync.is-pending" in css, "clinic public sync pending style missing")
    check(".clinic-public-sync.is-muted" in css, "clinic public sync muted style missing")
    check(".publish-readiness" in css, "publish readiness style missing")
    check(".publish-missing-chip" in css, "publish missing chip style missing")
    check(".publish-cell" in css, "clinic publish cell style missing")
    check(".publish-cell strong" in css, "clinic first missing field style missing")
    check(".publish-cell.is-web-pending strong" in css, "clinic web-pending style missing")
    check(".publish-web-note" in css, "clinic table web-pending note style missing")
    check(".field-attention" in css, "field attention style missing")
    check(".review-decision" in css, "review decision style missing")
    check(".review-decision-summary" in css, "review decision summary style missing")
    check(".review-proposal-focus" in css, "review proposal focus style missing")
    check(".review-current-relevant" in css, "review current data style missing")
    check(".review-selection-panel" in css, "review selection placeholder style missing")
    check(".review-evidence-panel" in css, "review evidence style missing")
    check(".review-warning-panel" in css, "review warning style missing")
    check(".review-modify-panel" in css, "review modify style missing")
    check(".review-decision-actions" in css, "review decision action style missing")
    print("OK admin publication flow: status consequences are visible")


if __name__ == "__main__":
    main()
