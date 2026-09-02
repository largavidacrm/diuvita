#!/usr/bin/env python3
"""Checks the clinic portal manual-review workflow wiring."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    migration = read("supabase/migrations/0023_clinic_portal.sql")
    build = read("build.py")
    admin = read("admin/index.html")
    portal_html = read("portal-clinicas/index.html")
    portal_js = read("portal-clinicas/portal.js")
    portal_css = read("portal-clinicas/portal.css")
    docs = read("docs/CLINIC_PORTAL.md")

    for marker in [
        "create table if not exists public.clinic_claim_requests",
        "create table if not exists public.clinic_portal_memberships",
        "create table if not exists public.clinic_profile_change_requests",
        "alter table public.clinics",
        "identity_confirmed_at",
        "portal_submit_clinic_claim_request",
        "portal_submit_profile_change_request",
        "portal_my_clinic_workspace",
        "admin_resolve_clinic_claim_request",
        "admin_resolve_clinic_profile_change_request",
        "'clinic_claim_request'",
        "'clinic_profile_enrichment'",
        "'candidate_clinic'",
        "'source', 'clinic_portal'",
        "'id', c.id",
        "'portal'",
        "enable row level security",
        "portal_filter_profile_fields",
    ]:
        check(marker in migration, f"missing migration marker: {marker}")

    for marker in [
        "def write_clinic_portal():",
        "def portal_clinic_list():",
        '"/portal-clinicas/"',
        "confirmed_badge",
        "Datos confirmados por el centro",
        "Reclamar o corregir esta ficha",
        '"identity_confirmed_at"',
    ]:
        check(marker in build, f"missing build marker: {marker}")

    for marker in [
        'id="claimForm"',
        'id="recommendForm"',
        'id="loginForm"',
        'id="workspacePanel"',
        'id="changeForm"',
        "window.VITALARGA_PORTAL_CONFIG",
        "window.VITALARGA_PORTAL_CLINICS",
        "Enviar reclamación",
        "Enviar recomendación",
        "Enviar cambios para validar",
    ]:
        check(marker in portal_html, f"missing portal HTML marker: {marker}")

    for marker in [
        "portal_submit_clinic_claim_request",
        "portal_submit_profile_change_request",
        "portal_my_clinic_workspace",
        "signInWithOtp",
        'p_request_kind: "claim_existing"',
        'p_request_kind: "recommend_clinic"',
        "p_accept_manual_review",
        "proposedFieldsFromForm",
        "Nada se publica automáticamente",
        "completeIntakeSubmission",
        'show(el("claimForm"), false)',
        'show(el("recommendForm"), false)',
        "¡Muchas gracias! Revisaremos tu solicitud manualmente con la mayor brevedad posible.",
    ]:
        combined = portal_js + "\n" + portal_html
        check(marker in combined, f"missing portal JS/HTML marker: {marker}")

    for marker in [
        "portal-layout",
        "mode-tabs",
        "workspace-grid",
        "status-pill",
        ".btn{",
        ".portal-message.success",
        "@media(max-width:900px)",
    ]:
        check(marker in portal_css, f"missing portal style marker: {marker}")

    for marker in [
        '["clinic_claim_request", "Reclamaciones"]',
        'clinic_claim_request: "Reclamación de ficha"',
        "function isClinicClaimReview",
        "function isPortalChangeReview",
        "admin_resolve_clinic_profile_change_request",
        "function approveReview",
        "function rejectReview",
        "function modifyReview",
        "clinicClaimReviewItems",
        "portalRiskItems",
        "reviewProposalFocus",
        "reviewEvidencePanel",
        "reviewWarningPanel",
        "Mensaje del formulario",
        "No cambia datos públicos ni concede acceso",
        "Propuesta cerrada. Elige la siguiente revisión en la lista.",
    ]:
        check(marker in admin, f"missing admin marker: {marker}")

    check('type="file"' not in portal_html.lower(), "portal should not include document uploads yet")
    strong_badge = "Clínica " + "Verificada"
    check(strong_badge not in (portal_html + "\n" + build + "\n" + admin), "avoid strong verified-clinic badge wording")
    check("smtp" not in portal_js.lower(), "portal should not send outbound email directly")

    for marker in [
        "nada se publica automáticamente",
        "Deliberadamente fuera de esta fase",
        "Subida de CIF",
        "Emails salientes enviados por Vitalarga",
        "Antes de activar en producción",
    ]:
        check(marker in docs, f"missing portal documentation marker: {marker}")

    print("OK clinic portal: manual-review portal wiring present")


if __name__ == "__main__":
    main()
