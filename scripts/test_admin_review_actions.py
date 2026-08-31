#!/usr/bin/env python3
"""Checks that admin review proposals stay single-decision and traceable."""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        'id="reviewSearch"',
        'id="reviewTypeFilter"',
        'id="reviewPriorityFilter"',
        'id="reviewListPanel"',
        'id="reviewsBody"',
        'class="review-table"',
        'data-review-id',
        'id="reviewClinicPanel"',
        'id="reviewClinicProfileMeta"',
        'id="reviewClinicProfileStatus"',
        'id="reviewClinicProfileName"',
        'id="reviewClinicProfileSummary"',
        'id="reviewClinicProfileFacts"',
        'id="reviewClinicProfileDataCount"',
        'id="reviewClinicProfileData"',
        'id="reviewBackToListBtn"',
        'id="reviewSelectionPanel"',
        'id="reviewDecisionSummary"',
        'id="reviewAffectedClinic"',
        'id="reviewAffectedClinicMeta"',
        'id="reviewProposalType"',
        'id="reviewProposalDate"',
        'id="reviewCurrentRelevantPanel"',
        'id="reviewCurrentRelevantCount"',
        'id="reviewCurrentRelevantList"',
        'id="reviewProposalFocus"',
        'id="reviewProposalFocusTitle"',
        'id="reviewProposalFocusMeta"',
        'id="reviewProposalFocusCount"',
        'id="reviewProposalFocusList"',
        'id="reviewEvidencePanel"',
        'id="reviewEvidenceCount"',
        'id="reviewSourceOrigin"',
        'id="reviewEvidenceList"',
        'id="reviewWarningPanel"',
        'id="reviewWarningCount"',
        'id="reviewWarningList"',
        'id="reviewModifyPanel"',
        'id="reviewModifyFields"',
        'id="reviewSourceJobPanel"',
        'id="reviewSourceJobUrl"',
        'id="reviewSourceJobBtn"',
        'id="reviewResolutionNote"',
        'id="reviewApproveBtn"',
        'id="reviewRejectBtn"',
        'id="reviewModifyBtn"',
        'id="clinicInternalContactName"',
        'id="clinicInternalContactEmail"',
        'id="clinicInternalContactPhone"',
        'id="clinicInternalContactNote"',
        'id="clinicManualReviewContext"',
        'id="clinicManualReviewField"',
        'id="clinicManualReviewIssue"',
        'id="clinicManualReviewMeta"',
        'id="clinicManualReviewFocusBtn"',
        'id="clinicManualReviewSourceWrap"',
        'id="clinicManualReviewSourceUrl"',
        'id="clinicManualReviewSourceBtn"',
        ">Aprobar</button>",
        ">Rechazar</button>",
        ">Modificar</button>",
        "function reviewModifyIdleLabel",
        "Editar ficha",
        "Revisión manual",
        "data-review-manual-field",
        "Modificar contacto",
        "Ficha de la clínica",
        "Datos visibles en la ficha",
        "Contacto interno",
        "Campo a corregir: ",
        "Dato pendiente: ",
        "Guarda la ficha para cerrar esta revisión y pasar a la siguiente.",
        "Dile al agente dónde mirar",
        "Enviar URL al agente",
        "Confirmar misma ficha",
        "review-proposal-title",
        "review-proposal-hint",
        "Clínica afectada",
        "Tipo de propuesta",
        "Datos actuales relevantes",
        "Cambio propuesto",
        "Fuente o evidencia",
        "URL aportada por Daniel",
        "Advertencias imprescindibles",
        "Observación breve",
    ]:
        check(marker in index, f"missing single-decision review marker: {marker}")

    for removed_dom in [
        'id="reviewActionNote"',
        'id="reviewFlowPanel"',
        'id="reviewGuidancePanel"',
        'id="relatedReviewsPanel"',
        'id="reviewClinicSnapshot"',
        'id="reviewCreateDraftBtn"',
        'id="reviewDismissBtn"',
        'data-load-related-proposals',
        'data-related-review-id',
    ]:
        check(removed_dom not in index, f"old chained review UI should not be present: {removed_dom}")

    check("Cargar mejoras juntas" not in index, "single proposals should not offer grouped loading")
    check("Ver solicitud" not in index and "Confirmar identidad" not in index and "Cerrar tarjeta" not in index, "old review steps should be removed")
    check('class="review-flow-step"' not in index, "old oversized step cards should be removed")

    editor_start = index.index('id="reviewEditor"')
    editor_end = index.index('<section class="panel" id="jobsPanel"', editor_start)
    review_editor = index[editor_start:editor_end]
    for forbidden in [
        "Camino de publicación",
        "Recomendaciones generales",
        "Resumen de cola",
        "Trabajos recientes",
        "Otras revisiones",
        "Atajos",
        "Auditorías",
        "Cargar mejoras juntas",
    ]:
        check(forbidden not in review_editor, f"open proposal editor should stay focused, found: {forbidden}")
    decision_tail = review_editor[review_editor.index('id="reviewModifyBtn"'):]
    check("<section" not in decision_tail, "no extra proposal content should appear after the three decisions")

    check(
        index.index('id="reviewCurrentRelevantPanel"')
        < index.index('id="reviewProposalFocus"')
        < index.index('id="reviewEvidencePanel"')
        < index.index('id="reviewWarningPanel"')
        < index.index('id="reviewModifyPanel"')
        < index.index('id="reviewApproveBtn"')
        < index.index('id="reviewRejectBtn"')
        < index.index('id="reviewModifyBtn"'),
        "review editor should end with the three decision actions",
    )

    check(
        "function candidateReviewSources" in index
        and "candidate.source_urls" in index
        and "function reviewEvidenceItems" in index
        and "candidateReviewSources(candidate, payload, source).forEach" in index
        and "proposalLinkItems(payload).forEach" in index,
        "candidate evidence should keep all source URLs in the focused evidence block",
    )
    check(
        'value="clinic_claim_request"' in index
        and "function isClinicClaimRequestReview" in index
        and "Reclamación de ficha" in index
        and "No confirma identidad, no da acceso y no cambia datos" in index
        and "Cerrar reclamación" in index
        and "Reclamación cerrada sin cambios en la ficha." in index,
        "clinic claim requests should be a human-only review flow",
    )
    check(
        "function claimRequestContactFromReview" in index
        and "function approveClinicClaimRequestReview" in index
        and "Contacto interno registrado desde reclamación de ficha" in index
        and "No cambia datos públicos ni concede acceso" in index
        and 'draft.currentData.internal_contact' in index
        and "function cleanInternalClinicContact" in index
        and 'clean.visibility = "internal"' in index,
        "clinic claim requests should register a private clinic contact without web publication",
    )
    check(
        'return /^https?:\\/\\//i.test(clean) ? clean : "";' in index
        and '["maps_url", "Google Maps", "maps_url"]' in index
        and '["google_reviews_url", "Valoraciones Google", "google_reviews_url"]' in index
        and '["reviews_url", "Valoraciones Google", "google_reviews_url"]' in index
        and '["pricing_url", "Página de precios", "pricing_url"]' in index,
        "proposed review links should be safe and cover Maps/reviews/pricing",
    )
    check(
        "parece búsqueda, ruta o dirección" in index
        and "falta señal clara de ficha de clínica" in index
        and '" · sede principal"' in index
        and '" · sede adicional"' in index,
        "proposed Google Maps links should warn on weak URLs without numbered sede labels",
    )
    check(
        "function canonicalProposalField" in index
        and "function mergeReviewPayloads(rows)" in index
        and "function loadRelatedEnrichmentProposals()" in index
        and "function relatedOpenReviews" in index
        and "function clinicReviewBundle" in index
        and "function reviewWorkgroupRecommendation" in index
        and "activeClinicReviewIds" in index,
        "group analysis helpers should remain available for future automation",
    )
    check(
        "Ficha actualizada desde revisión manual." in index
        and "alguna tarjeta no se cerró automáticamente" in index
        and "Conflicto en " in index,
        "legacy grouped-save safeguards should remain safe and non-public",
    )
    check(
        'phone: "telefono"' in index
        and 'telephone: "telefono"' in index
        and 'professionals: "profesionales"' in index
        and "var key = canonicalProposalField(rawKey);" in index
        and "function splitSpanishPhones" in index
        and "function expandedPhoneProposalFields" in index
        and "function mergeScalarProposalField" in index
        and "Telefonos separados: revisa principal, fijo y movil antes de guardar." in index
        and "function proposalPhoneWarning" in index
        and "phone: \"clinicPhone\"" in index
        and "telephone: \"clinicPhone\"" in index
        and "tech: true" in index,
        "grouped proposals should normalize aliases, merge technology and warn on weak phones",
    )
    check(
        "function approveReview" in index
        and "function approveExistingClinicReview" in index
        and "function approveCandidateReview" in index
        and "function rejectReview" in index
        and "function modifyReview" in index
        and "function finishReviewDecision" in index
        and "function renderReviewClinicPanel" in index
        and "function reviewProposalFocusHint" in index
        and "function reviewProposalFocusActionHtml" in index
        and "function reviewMissingFieldTargetsForText" in index
        and "function reviewMissingFieldTargets" in index
        and "function reviewHasManualFieldRoute" in index
        and "function reviewManualFieldTarget" in index
        and "function openClinicEditorForReview" in index
        and "function openReviewManualField" in index
        and "function reviewSourceJobTargets" in index
        and "function reviewSourceJobTargetScope" in index
        and "function reviewSourceJobContext" in index
        and "function createReviewSourceJobFor" in index
        and "function createClinicManualReviewSourceJob" in index
        and "function createReviewSourceJob" in index
        and '"EXTRACT_CLINIC_PROFILE"' in index
        and "from_review_id" in index
        and "human_supplied_source" in index
        and "operator_intent" in index
        and "allowed_output" in index
        and "reviewSourceJobExampleForTargets" in index
        and "requested_fields" in index
        and "requested_field_labels" in index
        and "missing_fields" in index
        and "function reviewClinicProfileFacts" in index
        and "function reviewClinicProfileDataItems" in index
        and "function reviewClinicProfileValue" in index
        and 'await finishReviewDecision(modified ? "Modificación guardada." : "Propuesta aprobada.", currentId)' in index
        and 'await finishReviewDecision("Propuesta rechazada.", currentId)' in index
        and "openReviewEditor(nextReview.id)" in index
        and "Cola terminada. No quedan propuestas pendientes." in index
        and "admin_update_clinic" in index
        and "admin_create_draft_clinic_from_review_v2" in index
        and "admin_resolve_review_item" in index,
        "approve, reject and modify should resolve one proposal and continue the queue",
    )
    check(
        'item.action !== "Revisión manual"' in index
        and "openClinicEditorForReview(activeReview, targetId || firstReviewMissingFieldTargetId(activeReview))" in index
        and 'el("reviewProposalFocusList").addEventListener("click"' in index,
        "quality audit fields should offer direct manual review into the matching clinic field",
    )
    check(
        "if (reviewHasManualFieldRoute(activeReview))" in index
        and "openClinicEditorForReview(activeReview, firstReviewMissingFieldTargetId(activeReview));" in index
        and "focusPublishField(activeClinicReviewFocusTarget.inputId);" in index,
        "manual review cards should open the clinic editor directly at the pending field",
    )
    check(
        '"Completar en ficha"' not in index
        and "function reviewDisplayTitle" in index
        and 'title.replace(/^Completar ficha:/i, "Revisión manual:")' in index
        and 'el("reviewEditorTitle").textContent = reviewDisplayTitle(activeReview)' in index,
        "quality-audit review UI should say manual review instead of completing a ficha",
    )
    check(
        "function renderClinicManualReviewContext" in index
        and "function reviewManualIssueForTarget" in index
        and "reviewSourceJobContext(activeClinicReview, activeClinicReviewFocusTarget)" in index
        and "createClinicManualReviewSourceJob" in index
        and "activeClinicReviewFocusTarget" in index
        and "focusPublishField(activeClinicReviewFocusTarget.inputId)" in index
        and "renderClinicManualReviewContext();" in index
        and "activeClinicReviewFocusTarget = reviewManualTargetForInput(row, focusTarget)" in index,
        "manual review clinic editor should show the exact field and refocus it",
    )
    check(
        "return focusedTargets.length ? focusedTargets : fallbackTargets;" in index
        and 'createReviewSourceJobFor(activeClinicReview, "clinicManualReviewSourceUrl", "clinicManualReviewSourceBtn", activeClinicReviewFocusTarget)' in index
        and "var targets = sourceJob.targets;" in index,
        "manual-review source jobs should target the focused field before falling back to all missing fields",
    )
    check(
        'target_scope: sourceJob.targetScope' in index
        and 'ui_route: sourceJob.uiRoute' in index
        and 'primary_requested_fields: targets.slice(0, 1).map(function (item) { return item.key; })' in index
        and 'primary_requested_field_labels: targets.slice(0, 1).map(function (item) { return item.label; })' in index,
        "source jobs should persist the UI route and primary field scope",
    )
    check(
        'payload.ui_route === "manual_review_banner_source_handoff"' in index
        and "Campo pedido: " in index
        and "Alcance: primero el campo activo" in index,
        "review evidence should explain Daniel-supplied source scope",
    )
    check(
        'show(el("jobCreatePanel"), false)' in index
        and 'show(el("reviewListPanel"), false)' in index
        and 'show(el("reviewClinicPanel"), true)' in index
        and 'show(el("reviewSelectionPanel"), false)' in index
        and 'show(el("reviewEditor"), true)' in index
        and 'show(el("reviewActionStrip"), false)' in index
        and 'show(el("reviewCasePanel"), false)' in index,
        "opening a review should hide the queue and show the clinic ficha beside the decision",
    )
    check(
        'show(el("reviewActionStrip"), false);' in index
        and '"Caso recomendado"' not in index
        and '"Acción recomendada"' not in index,
        "review queue should not show oversized recommendation panels by default",
    )
    check(
        "Abre el enlace y confirma que es el perfil real de la clínica antes de aprobar." in index
        and "Comprueba que las valoraciones pertenecen a la misma ficha de Google Maps de la clínica." in index
        and "Alguna sede trae Google Maps dudoso" in index,
        "Google Maps proposals should show actionable in-card review hints",
    )
    check(
        "function proposalGoogleMapsStatus" in index
        and "function proposalReviewStatusHtml" in index
        and "Parece perfil directo" in index
        and "No guardar tal cual" in index
        and "review-link-status" in index,
        "Google Maps proposals should show a compact link-status verdict",
    )
    check(
        'show(el("reviewClinicPanel"), false)' in index
        and 'show(el("reviewListPanel"), true)' in index
        and 'el("reviewBackToListBtn").addEventListener("click", closeReviewEditor)' in index,
        "closing a review should restore the queue view",
    )
    check(
        'class="review-decision-summary hidden"' in index
        and 'class="review-current-relevant hidden"' in index,
        "current clinic context should move out of the visible decision column",
    )
    check(
        index.index('id="reviewListPanel"')
        < index.index('id="reviewClinicPanel"')
        < index.index('id="reviewSelectionPanel"')
        < index.index('id="reviewEditor"'),
        "review work area should switch from queue to clinic ficha before the decision panel",
    )
    check(
        'reviewType === "clinic_claim_request"' in index
        and "Reclamación sin ficha enlazada. No crearé un borrador automáticamente." in index
        and "Reclamación abierta. No concede acceso ni cambia datos automáticamente." in index
        and 'admin_create_draft_clinic_from_review_v2' in index,
        "clinic claim requests should open existing clinic context instead of creating a draft",
    )
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")
    check(".review-decision" in css, "single decision container should be styled")
    check(".review-table" in css, "review queue table should have compact dedicated styling")
    check(".review-work-list-only" not in css and "review-work-list-only" not in index, "review queue should keep the two-column work area")
    check(
        "review-selection-empty" in index
        and "Pulsa Revisar y verás aquí la ficha afectada y el cambio concreto para decidir." in index,
        "review queue should keep a visible right-side selection panel",
    )
    tablet_chunk = css[css.index("@media (max-width: 860px)"):css.index("@media (max-width: 700px)")]
    check(".work-grid" not in tablet_chunk, "review work area should not collapse before narrow mobile widths")
    check(
        "@media (max-width: 700px)" in css
        and ".work-grid {\n    grid-template-columns: 1fr;" in css,
        "review work area should stack only on narrow mobile screens",
    )
    check(".review-decision-summary" in css, "review decision summary should be styled")
    check(".review-clinic-panel" in css and ".review-clinic-profile" in css, "review clinic ficha panel should be styled")
    check(".review-clinic-facts" in css and ".review-clinic-data-panel" in css, "review clinic ficha details should be styled")
    check(".clinic-manual-review-context" in css and ".clinic-manual-source" in css, "manual review context and source handoff should be styled")
    check(".review-proposal-title" in css and ".review-proposal-hint" in css and ".review-manual-btn" in css, "proposal action hints should be styled")
    check(".review-link-status" in css and ".review-link-status-warning" in css, "proposal link status should be styled")
    check(".review-source-origin" in css, "Daniel-supplied source origin should be styled")
    check(".review-proposal-focus" in css and ".review-current-relevant" in css, "current/proposed decision panels should be styled")
    check(".review-evidence-panel" in css and ".review-warning-panel" in css, "evidence/warning panels should be styled")
    check(".review-modify-panel" in css and ".review-source-job-panel" in css and ".review-decision-actions" in css, "modify, source job and action panels should be styled")
    check("grid-template-columns: repeat(3, minmax(0, 1fr))" in css, "three review actions should share one row")
    check("quick-primary" in index and "quick-action" in index, "quick review actions should be classified")
    check("review-action-lead" in index and "review-action-buttons" in index, "quick review actions should have lead copy and grouped buttons")
    check(
        index.index('id="reviewActionStrip"') < index.index('id="reviewSearch"'),
        "recommended review action should appear before search filters",
    )
    lead_match = re.search(r"function reviewActionLeadCopy\([\s\S]+?\n    \}", index)
    check(lead_match is not None, "review action lead copy function missing")
    check(
        '"Abrir prioridad: " + reviewPrimarySubject(nextReview)' not in lead_match.group(0),
        "review action title should not include long dynamic subjects",
    )
    check(".review-action-strip .quick-primary" in css, "primary quick action should be styled")
    check("grid-template-columns: minmax(220px, 0.85fr) minmax(0, 1.15fr)" in css, "quick actions should use a compact lead/buttons grid")
    check(".review-action-buttons" in css and "repeat(auto-fit, minmax(8.4rem, 1fr))" in css, "quick action buttons should be gridded")
    check("grid-template-columns: 1fr" in css, "quick actions should stack on mobile")
    print("OK admin review actions: single-decision queue flow")


if __name__ == "__main__":
    main()
