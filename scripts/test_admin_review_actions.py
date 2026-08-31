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
        'id="reviewsBody"',
        'data-review-id',
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
        'id="reviewEvidenceList"',
        'id="reviewWarningPanel"',
        'id="reviewWarningCount"',
        'id="reviewWarningList"',
        'id="reviewModifyPanel"',
        'id="reviewModifyFields"',
        'id="reviewResolutionNote"',
        'id="reviewApproveBtn"',
        'id="reviewRejectBtn"',
        'id="reviewModifyBtn"',
        ">Aprobar</button>",
        ">Rechazar</button>",
        ">Modificar</button>",
        "Clínica afectada",
        "Tipo de propuesta",
        "Datos actuales relevantes",
        "Cambio propuesto",
        "Fuente o evidencia",
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
        'show(el("jobCreatePanel"), false)' in index
        and 'show(el("reviewSelectionPanel"), false)' in index
        and 'show(el("reviewEditor"), true)' in index
        and 'show(el("reviewActionStrip"), false)' in index
        and 'show(el("reviewCasePanel"), false)' in index,
        "opening a review should hide non-decision panels",
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
    check(".review-decision-summary" in css, "review decision summary should be styled")
    check(".review-proposal-focus" in css and ".review-current-relevant" in css, "current/proposed decision panels should be styled")
    check(".review-evidence-panel" in css and ".review-warning-panel" in css, "evidence/warning panels should be styled")
    check(".review-modify-panel" in css and ".review-decision-actions" in css, "modify and action panels should be styled")
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
