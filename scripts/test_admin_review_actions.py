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
        'class="panel review-panel review-list-panel"',
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
        'id="reviewClinicPendingPanel"',
        'id="reviewClinicPendingCount"',
        'id="reviewClinicPendingList"',
        'id="reviewClinicInlineEditBtn"',
        'id="reviewClinicEditPanel"',
        'id="reviewClinicEditChangeCount"',
        'id="reviewClinicEditName"',
        'id="reviewClinicEditSummary"',
        'id="reviewClinicEditWebsite"',
        'id="reviewClinicEditLocations"',
        'id="reviewClinicEditServices"',
        'id="reviewClinicEditProfessionals"',
        'id="reviewClinicEditPhone"',
        'id="reviewClinicEditInternalContactName"',
        'id="reviewClinicEditInternalContactEmail"',
        'id="reviewClinicEditInternalContactPhone"',
        'id="reviewClinicEditInternalContactNote"',
        'id="reviewClinicEditChanges"',
        'id="reviewClinicEditChangesList"',
        'id="reviewClinicEditHint"',
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
        "Revisión manual",
        "data-review-manual-field",
        "Modificar contacto",
        "Ficha de la clínica",
        "Mejoras acumuladas en esta ficha",
        "Datos visibles en la ficha",
        "Contacto interno",
        "Campo a revisar ahora",
        "Campo a corregir: ",
        "Dato pendiente: ",
        "Guarda la ficha para cerrar esta revisión y volver a la lista.",
        "Los cambios se aplican solo si apruebas o guardas la modificación.",
        "Cambios manuales preparados",
        "URL oficial para el agente",
        "Enviar URL al agente",
        "Editar en ficha",
        "review-proposal-title",
        "review-proposal-hint",
        "Clínica afectada",
        "Tipo de propuesta",
        "Datos actuales relevantes",
        "Cambio propuesto",
        "Fuente o evidencia",
        "URL aportada por Daniel",
        "Puedes decidir o modificar esta propuesta manualmente.",
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
    editor_end = index.index('<section class="panel job-create-panel"', editor_start)
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
        "function isPortalChangeReview" in index
        and "function portalChangeRequestId" in index
        and "admin_resolve_clinic_profile_change_request" in index
        and "reviewSourceJobPanel" in index,
        "portal-originated profile changes should close through the current focused review flow",
    )
    check(
        'id="reviewContextPanel"' not in index
        and 'id="reviewProfilePanel"' not in index
        and 'id="reviewNeedsInfoBtn"' not in index,
        "review editor should not render the old portal context panels",
    )
    check(
        'return /^https?:\\/\\//i.test(clean) ? clean : "";' in index
        and '["maps_url", "Google Maps", "maps_url"]' in index
        and '["pricing_url", "Página de precios", "pricing_url"]' in index,
        "proposed review links should be safe and cover Maps/pricing",
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
        and "function reviewQueueGroups" in index
        and "function reviewQueueGroupPrimaryRow" in index
        and "function reviewQueueGroupSubjectCell" in index
        and "function renderReviewClinicPendingPanel" in index
        and "function reviewClinicPendingRows" in index
        and "function reviewWorkgroupRecommendation" in index
        and "activeClinicReviewIds" in index,
        "clinic grouping helpers should keep one ficha per clinic while preserving atomic review rows",
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
        and "function reviewActiveManualTarget" in index
        and "function focusManualReviewFieldTarget" in index
        and "function focusManualReviewFieldTargetDirectly" in index
        and "function markManualReviewFieldTarget" in index
        and "function openClinicEditorForReview" in index
        and "function openReviewManualField" in index
        and "function fieldsHaveReviewedMapsContext" in index
        and "function reviewSourceJobTargets" in index
        and "function reviewSourceJobTargetScope" in index
        and "function reviewSourceJobContext" in index
        and "function reviewNeedsSpecialistSourceHandoff" in index
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
        and "var profileFields = reviewClinicProfileEditedFields(activeReview);" in index
        and "var decisionModified = Boolean(modified || Object.keys(profileFields).length);" in index
        and 'await finishReviewDecision(decisionModified ? "Modificación guardada." : "Propuesta aprobada.", currentId)' in index
        and 'await finishReviewDecision("Propuesta rechazada.", currentId)' in index
        and "Propuesta cerrada. Elige la siguiente revisión en la lista." in index
        and "Vuelvo a la lista." in index
        and "Paso a la siguiente propuesta." not in index
        and "Clínica guardada. Paso a la siguiente propuesta." not in index
        and "admin_update_clinic" in index
        and "admin_create_draft_clinic_from_review_v2" in index
        and "admin_resolve_review_item" in index,
        "approve, reject and modify should resolve one proposal and return to the review list",
    )
    check(
        "var activeReviewProfileEditMode = false" in index
        and "function reviewClinicProfileEditDefinitions" in index
        and "function reviewClinicProfileEditListDisplayValue" in index
        and "function populateReviewClinicEditFields" in index
        and "function reviewClinicProfileEditedFieldItems" in index
        and "function reviewClinicProfileEditedFields" in index
        and "function renderReviewClinicEditChanges" in index
        and "function updateReviewClinicEditChangeCount" in index
        and "function setReviewClinicEditMode" in index
        and "function toggleReviewClinicInlineEdit" in index
        and "function applyProfileEditFieldsToDraft" in index
        and "applyProfileEditFieldsToDraft(draft, profileFields)" in index
        and 'key: "internal_contact"' in index
        and "setClinicInternalContact(draft.currentData, value)" in index
        and "candidate.internal_contact = cleanInternalClinicContact(value)" in index
        and "persistModifiedCandidatePayload(activeReview, combinedFields)" in index
        and "Object.keys(reviewClinicProfileEditedFields(activeReview)).length && !reviewEditableItems(activeReview).length" in index
        and 'el("reviewClinicInlineEditBtn").addEventListener("click", toggleReviewClinicInlineEdit)' in index
        and 'el("reviewClinicEditPanel").addEventListener("input", updateReviewClinicEditChangeCount)' in index
        and 'el("reviewClinicEditPanel").addEventListener("change", updateReviewClinicEditChangeCount)' in index,
        "selected clinic side panel should allow direct profile edits that are saved only through approve/modify",
    )
    check(
        'item.action !== "Revisión manual"' in index
        and ">Editar en ficha</button>" in index
        and "openClinicEditorForReview(activeReview, targetId || firstReviewMissingFieldTargetId(activeReview))" in index
        and 'el("reviewProposalFocusList").addEventListener("click"' in index,
        "quality audit fields should offer direct manual review into the matching clinic field",
    )
    check(
        "function specialistNoiseReason" in index
        and "function suspiciousSpecialistValues" in index
        and "function proposalSpecialistsStatus" in index
        and "function reviewApprovalBlockReason" in index
        and "function reviewFieldApprovalConfirmationReason" in index
        and "function noisySpecialistApprovalConfirmation" in index
        and "function confirmNoisySpecialistApproval" in index
        and "Especialistas contiene entradas sospechosas" in index
        and "Corregir antes de aprobar" in index
        and "Usa Modificar y deja solo nombres claros" in index
        and "Daniel puede aprobarla igualmente si la ha revisado" in index
        and "Si has revisado la fuente y quieres aceptarlo igualmente como decisión humana, confirma" in index
        and "confirmedNoisySpecialists" in index
        and "window.confirm(message)" in index
        and "humanModifiedSpecialists" in index
        and "Boolean(reviewApprovalBlockReason(activeReview))" in index
        and "var approvalBlock = reviewApprovalBlockReason(activeReview);" in index
        and 'data-review-field-confirm="noisy-specialists"' in index,
        "dirty specialist proposals should warn and require explicit human confirmation before approval",
    )
    review_block_start = index.index("function reviewApprovalBlockReason")
    review_block_end = index.index("function noisySpecialistApprovalExamples", review_block_start)
    check(
        "reviewHasNoisySpecialistProposal" not in index[review_block_start:review_block_end],
        "dirty specialists should not disable Daniel's main approve button",
    )
    check(
        "function reviewSupportsInlineFieldDecision" in index
        and "function reviewProposalFieldActionsHtml" in index
        and 'data-review-field-action="approve"' in index
        and 'data-review-field-action="reject"' in index
        and 'data-review-field-action="edit"' in index
        and 'data-review-field-action="confirm"' in index
        and "function approveReviewField" in index
        and "function rejectReviewField" in index
        and "function handleReviewFieldAction" in index
        and "function reviewPayloadAfterFieldDecision" in index
        and "field_decisions" in index
        and "saveExistingClinicReviewFields(fields, Boolean(modified), {}, note, {" in index
        and "Campo guardado." in index
        and "Quedan " in index,
        "profile-enrichment proposal fields should be directly approvable, rejectable or editable in-card",
    )
    check(
        "function resetReviewWorkAreaForNav" in index
        and 'if (targetId === "reviewWorkArea") resetReviewWorkAreaForNav();' in index
        and "show(el(\"reviewListPanel\"), true);" in index
        and "setReviewWorkMode(\"queue\");" in index,
        "sidebar review navigation should restore the review inbox when a subview is open",
    )
    check(
        index.index('id="reviewProposalFocusList"')
        < index.index('id="reviewSourceJobPanel"')
        < index.index('id="reviewEvidencePanel"')
        and 'show(el("reviewEvidencePanel"), Boolean(items.length || origin.text));' in index
        and 'target ? target.label : "Campo pendiente"' in index,
        "manual source help should live inside the active proposal and empty evidence should stay hidden",
    )
    check(
        "function openReviewEntry" in index
        and "openReviewEditor(id);" in index
        and "reviewHasManualFieldRoute(row) && openClinicEditorForReview(row, firstReviewMissingFieldTargetId(row))" not in index
        and 'if (button) openReviewEntry(button.getAttribute("data-review-id"))' in index
        and "if (id) openReviewEntry(id)" in index
        and "visibleAuditIssues = isBlockingClaimReview(row) ? auditIssues : auditIssues.slice(0, 1)" in index
        and "focusManualReviewFieldTargetDirectly(manualTarget);" in index
        and "activeClinicReviewFocusTarget = manualTarget;" in index,
        "manual review queue entries should open the proposal columns before any focused field edit",
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
        and "function finishManualQualityReviewAfterSave" in index
        and "function manualReviewTargetSatisfied" in index
        and "reviewSourceJobContext(activeClinicReview, activeClinicReviewFocusTarget)" in index
        and "createClinicManualReviewSourceJob" in index
        and "activeClinicReviewFocusTarget" in index
        and "focusManualReviewFieldTargetDirectly(activeClinicReviewFocusTarget)" in index
        and "renderClinicManualReviewContext();" in index
        and "activeClinicReviewFocusTarget = manualTarget;" in index
        and "var manualTarget = reviewManualTargetForInput(row, focusTarget)" in index,
        "manual review clinic editor should show the exact field and refocus it",
    )
    check(
        "manual_review_progress" in index
        and ".from(\"review_queue\")" in index
        and ".update({ payload: nextPayload })" in index
        and "Campo guardado. La revisión vuelve a la lista con los pendientes restantes." in index
        and "Ficha guardada, pero ese campo sigue pendiente. Lo mantengo abierto." in index,
        "manual review saves should resolve only the active missing field and return to the list",
    )
    check(
        "return focusedTargets.length ? focusedTargets : fallbackTargets;" in index
        and "reviewSourceJobContext(row, reviewActiveManualTarget(row))" in index
        and 'createReviewSourceJobFor(activeReview, "reviewSourceJobUrl", "reviewSourceJobBtn", reviewActiveManualTarget(activeReview))' in index
        and 'createReviewSourceJobFor(activeClinicReview, "clinicManualReviewSourceUrl", "clinicManualReviewSourceBtn", activeClinicReviewFocusTarget)' in index
        and "var targets = sourceJob.targets;" in index,
        "manual-review source jobs should target the focused field before falling back to all missing fields",
    )
    check(
        'target_scope: sourceJob.targetScope' in index
        and 'ui_route: sourceJob.uiRoute' in index
        and "operator_requested_field_summary: sourceJob.labels" in index
        and "llm_boundary: sourceJob.llmBoundary" in index
        and 'primary_requested_fields: targets.slice(0, 1).map(function (item) { return item.key; })' in index
        and 'primary_requested_field_labels: targets.slice(0, 1).map(function (item) { return item.label; })' in index,
        "source jobs should persist the UI route, primary field scope and LLM boundary",
    )
    check(
        "function reviewSourceJobPendingNote" in index
        and "function closeReviewWorkspaceAfterSourceJob" in index
        and 'resolveReviewItem(row.id, "resolved", reviewSourceJobPendingNote(sourceJob, url))' in index
        and "Fuente enviada al agente. Queda en cola para el ciclo CTO supervisado; volverá como propuesta cuando haya datos revisables." in index
        and "La tarjeta se cierra y queda sustituida si el ciclo CTO supervisado crea una propuesta revisable." in index
        and "Cierro esta revisión hasta que vuelva como propuesta." in index,
        "source jobs should close the originating review until the agent returns a proposal",
    )
    check(
        "function jobDetailText" in index
        and "function jobTitleText" in index
        and "function jobDateText" in index
        and '.select("job_type, status, confidence, cost_cents, created_at, scheduled_for, input")' in index
        and '.in("status", ["queued", "running"])' in index
        and 'id="pendingJobsBody"' in index
        and "Trabajos pendientes" in index
        and "URL desde revisión · " in index
        and "URL recomendada · " in index
        and "ciclo CTO supervisado · vuelve como propuesta revisable" in index
        and "En cola para ciclo CTO supervisado" in index
        and "function findPendingSourceJobDuplicate" in index
        and "function pendingJobMatchesSource" in index
        and "function jobComparableUrl" in index
        and "Ese link ya está en Trabajos pendientes" in index
        and "No creo duplicado" in index
        and "var recentJobRows = (jobRows.data || []).filter(function (row)" in index
        and 'return ["queued", "running"].indexOf(row.status) < 0;' in index
        and "recentJobRows.map(function (row)" in index
        and "jobDateText(row)" in index,
        "jobs table should explain pending jobs and keep them out of recent jobs",
    )
    check(
        "function reviewSourceJobOperatorIntent" in index
        and "Revisar solo especialistas y devolver una propuesta revisable" in index
        and "Revisar primero ese campo y devolver una propuesta revisable" in index
        and "Revisar solo esos campos y devolver propuestas revisables" in index,
        "source jobs should persist Daniel's bounded operator intent for later LLM help",
    )
    check(
        'payload.ui_route === "manual_review_banner_source_handoff"' in index
        and 'payload.ui_route === "review_card_specialist_source_handoff"' in index
        and "Campo pedido: " in index
        and "Alcance: primero el campo activo" in index,
        "review evidence should explain Daniel-supplied source scope",
    )
    check(
        'row.review_type === "clinic_profile_enrichment"' in index
        and "reviewProfessionalsCount(row) > 0" in index
        and "!reviewSpecialistSourceUrls(row).length" in index
        and '"review_card_specialist_source_handoff"' in index
        and '"specialist_source_only"' in index
        and '"Especialistas publicados"' in index,
        "specialist proposals without a clear source should allow a bounded source handoff",
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
        "if (!activeReview && !activeClinicReview)" in index
        and 'show(el("reviewListPanel"), true);' in index
        and 'show(el("reviewSelectionPanel"), true);' in index
        and 'setReviewWorkMode("queue");' in index,
        "review queue rendering should restore list and side panel when no review is active",
    )
    check(
        'class="work-grid review-work-queue" id="reviewWorkArea"' in index
        and "function setReviewWorkMode" in index
        and 'setReviewWorkMode("queue")' in index
        and 'setReviewWorkMode("decision")' in index
        and 'setReviewWorkMode("clinic-edit")' in index,
        "review work area should keep explicit queue, decision and clinic-edit layout modes",
    )
    check(
        'show(el("reviewActionStrip"), false);' in index
        and '"Caso recomendado"' not in index
        and '"Acción recomendada"' not in index,
        "review queue should not show oversized recommendation panels by default",
    )
    check(
        "Abre el enlace y confirma que es el perfil real de la clínica antes de aprobar." in index
        and "currentDataHasReviewedMaps(currentData)" in index
        and "Alguna sede trae Google Maps dudoso" in index
        and "Comprobación manual" in index
        and "El nombre visible en Google debe coincidir con:" in index
        and "No apruebes valoraciones aisladas sin esa coincidencia." not in index,
        "Google Maps proposals should show actionable in-card review hints",
    )
    check(
        "function proposalGoogleMapsStatus" in index
        and "function proposalReviewStatusHtml" in index
        and "function reviewMapsChecklistHtml" in index
        and "function reviewMapsExpectedClinicLabel" in index
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
        'reviewQueueGroups(rows)' in index
        and "reviewQueueGroupTypeSummary(entry)" in index
        and ">Revisar</button>" in index
        and "decisiones pendientes acumuladas" in index
        and "Ficha agrupada" in index
        and "decidirás una propuesta cada vez" in index,
        "review inbox should present one visible ficha per clinic with accumulated pending improvements",
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
    check("-webkit-line-clamp: 2" in css and "font-size: var(--text-ui)" in css, "review queue table should keep long rows visually compact")
    check(".review-work-list-only" not in css and "review-work-list-only" not in index, "review queue should keep the two-column work area")
    check(
        "review-selection-empty" in index
        and 'id="reviewSelectionOpenBtn"' in index
        and "function renderReviewQueueSelection" in index
        and "review-list-panel" in index
        and "Pulsa Revisar y verás aquí la ficha afectada y el cambio concreto para decidir." in index,
        "review queue should keep a visible right-side selection panel with a next-review action",
    )
    tablet_chunk = css[css.index("@media (max-width: 860px)"):css.index("@media (max-width: 700px)")]
    check(".work-grid" not in tablet_chunk, "review work area should not collapse before narrow mobile widths")
    check(
        "@media (max-width: 700px)" in css
        and ".work-grid.review-work-queue" in css
        and ".work-grid.review-work-decision" in css
        and "grid-template-columns: 1fr;" in css,
        "review work area should stack only on narrow mobile screens",
    )
    check(
        ".work-grid.review-work-queue" in css
        and ".work-grid.review-work-decision" in css
        and "minmax(0, 1fr) minmax(260px, 320px)" in css
        and "minmax(0, 0.95fr) minmax(400px, 1.05fr)" in css,
        "review queue and selected proposal should use stable desktop columns",
    )
    check(
        "window.requestAnimationFrame(function ()" in index
        and "focusManualReviewFieldTargetDirectly(manualTarget)" in index
        and "focusManualReviewFieldTargetDirectly(activeClinicReviewFocusTarget)" in index,
        "manual review actions should open and focus the exact clinic field directly",
    )
    check(".review-decision-summary" in css, "review decision summary should be styled")
    check(".review-clinic-panel" in css and ".review-clinic-profile" in css, "review clinic ficha panel should be styled")
    check(".review-clinic-facts" in css and ".review-clinic-data-panel" in css, "review clinic ficha details should be styled")
    check(".review-clinic-pending-panel" in css and ".review-clinic-pending-item" in css, "accumulated clinic review items should be styled")
    check(".review-clinic-edit-panel" in css and ".review-clinic-edit-grid" in css and ".review-clinic-edit-changes" in css and ".review-clinic-panel .link-btn.has-edits" in css, "review clinic direct edit panel should be styled")
    check(".clinic-manual-review-context" in css and ".clinic-manual-source" in css and ".manual-review-section" in css, "manual review context and source handoff should be styled")
    check(".work-grid.review-work-queue .review-list-panel" in css, "review queue side panel should stay explicit in CSS")
    check(".review-proposal-title" in css and ".review-proposal-hint" in css and ".review-manual-btn" in css, "proposal action hints should be styled")
    check(".review-proposal-actions" in css and ".review-proposal-inline-edit" in css, "in-card proposal decisions should be styled")
    check(".review-link-status" in css and ".review-link-status-warning" in css, "proposal link status should be styled")
    check(".review-link-checklist" in css and ".review-link-checklist li" in css, "Google Maps checklist should be styled")
    check(
        "function payloadHasReviewSourceContext" in index
        and "function reviewSourceOriginDetails" in index
        and "Fuente sin contexto de tarea: úsala solo como evidencia revisable, no como orden al LLM." in index
        and ".review-source-origin-source-only" in css,
        "source-only evidence should be visible without becoming LLM task context",
    )
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
