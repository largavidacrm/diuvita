#!/usr/bin/env python3
"""Checks for the read-only production health report."""

import check_production_health as health
from check_production_health import CHECKS, check_response, clean_base_url, format_report


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    ok_item = check_response("home", "https://example.test/", 200, "Vitalarga Buscar clínica", ["Vitalarga"])
    missing_item = check_response("admin", "https://example.test/admin/", 200, "Centro", ["Fichas completas"])
    error_item = check_response("profile", "https://example.test/profile", None, "", ["x"], "timeout")
    report = {
        "base_url": clean_base_url("https://example.test/"),
        "ok": False,
        "writes_data": False,
        "checks": [ok_item, missing_item, error_item],
    }
    output = format_report(report)

    check(ok_item["ok"] is True, "healthy response should pass")
    check(missing_item["ok"] is False, "missing markers should fail")
    check(error_item["ok"] is False, "network errors should fail")
    check(report["base_url"] == "https://example.test", "base url should be normalized")
    check("# Vitalarga production health" in output, "title missing")
    check("Estado: Atención" in output, "overall state missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("admin: Atención · 200" in output, "missing-marker line missing")
    check("faltan: Fichas completas" in output, "missing markers should be listed")
    check("profile: Atención · sin respuesta" in output, "error line missing")
    check("Attempts: 1" in output, "attempt count should be visible")
    original_run_checks = health.run_checks
    original_sleep = health.time.sleep
    calls = []

    def fake_run_checks(base_url, timeout):
        calls.append((base_url, timeout))
        return {
            "base_url": base_url,
            "ok": len(calls) > 1,
            "writes_data": False,
            "checks": [],
        }

    try:
        health.run_checks = fake_run_checks
        health.time.sleep = lambda _seconds: None
        retry_report = health.run_checks_with_retries("https://example.test", 3, retries=2, retry_delay=1)
    finally:
        health.run_checks = original_run_checks
        health.time.sleep = original_sleep

    check(retry_report["ok"] is True, "retry should allow a later healthy result")
    check(retry_report["attempts"] == 2, "retry attempts should be counted")
    check(len(calls) == 2, "health check should stop retrying after success")
    admin_check = [item for item in CHECKS if item["name"] == "admin_shell"][0]
    admin_css_check = [item for item in CHECKS if item["name"] == "admin_css"][0]
    home_check = [item for item in CHECKS if item["name"] == "home"][0]
    profile_check = [item for item in CHECKS if item["name"] == "public_profile_ux"][0]
    check("card-signals" in home_check["markers"], "home deployment should include card signal marker")
    check('class="logo-link"' in home_check["markers"], "home deployment should include clickable logo marker")
    check("clínicas visibles" not in home_check["markers"], "home deployment should not expect removed stats marker")
    check("Plan global" in admin_check["markers"], "admin deployment should include global plan title marker")
    check("globalPlanPanel" in admin_check["markers"], "admin deployment should include global plan panel marker")
    check("globalPlanOpenNextBtn" in admin_check["markers"], "admin deployment should include global plan next-action button marker")
    check("location-list" in profile_check["markers"], "profile deployment should include locations marker")
    check("section-count" not in profile_check["markers"], "profile deployment should not expect decorative counters")
    check("loadPublicationControl" in admin_check["markers"], "admin deployment should include publication control loader marker")
    check("Publicación web" in admin_check["markers"], "admin deployment should include manual publication marker")
    check("Duplicados mejoras" in admin_check["markers"], "admin deployment should include review-backlog marker")
    check("Contexto de grupo" in admin_check["markers"], "admin deployment should include clinic workgroup marker")
    check("Primer atasco" in admin_check["markers"], "admin deployment should include first backlog target marker")
    check("Freno bandeja" in admin_check["markers"], "admin deployment should include review backlog guard marker")
    check("loadSourceCoverage" in admin_check["markers"], "admin deployment should include source coverage loader marker")
    check("Fuentes por ficha" in admin_check["markers"], "admin deployment should include source coverage marker")
    check("Fichas sin fuente" in admin_check["markers"], "admin deployment should include source gap marker")
    check("Siguiente fuente" in admin_check["markers"], "admin deployment should include next source marker")
    check("openSourceTargetBtn" in admin_check["markers"], "admin deployment should include next source button marker")
    check("reviewDecisionSummary" in admin_check["markers"], "admin deployment should include review decision summary marker")
    check("reviewCurrentRelevantPanel" in admin_check["markers"], "admin deployment should include current relevant data marker")
    check("reviewClinicPanel" in admin_check["markers"], "admin deployment should include review clinic ficha marker")
    check("reviewProposalFocus" in admin_check["markers"], "admin deployment should include focused proposal marker")
    check("reviewEvidencePanel" in admin_check["markers"], "admin deployment should include evidence marker")
    check("reviewWarningPanel" in admin_check["markers"], "admin deployment should include warning marker")
    check("reviewApproveBtn" in admin_check["markers"], "admin deployment should include approve marker")
    check("reviewRejectBtn" in admin_check["markers"], "admin deployment should include reject marker")
    check("reviewModifyBtn" in admin_check["markers"], "admin deployment should include modify marker")
    check("sidebarToggleBtn" in admin_check["markers"], "admin deployment should include collapsible sidebar marker")
    check("reviewSourceJobPanel" in admin_check["markers"], "admin deployment should include review source handoff marker")
    check("clinicInternalContactName" in admin_check["markers"], "admin deployment should include private clinic contact marker")
    check("clinicManualReviewSourceBtn" in admin_check["markers"], "admin deployment should include manual-review source handoff marker")
    check("createReviewSourceJobFor" in admin_check["markers"], "admin deployment should include shared source-job creator")
    check("reviewSourceJobTargets" in admin_check["markers"], "admin deployment should include scoped source-job targets")
    check("target_scope: sourceJob.targetScope" in admin_check["markers"], "admin deployment should include source-job scope metadata")
    check("firstReviewMissingFieldTargetId" in admin_check["markers"], "admin deployment should include manual review field-focus marker")
    check("Prioridad: todas" in admin_check["markers"], "admin deployment should include compact priority filter marker")
    check("--text-ui" in admin_css_check["markers"], "admin css deployment should include UI text scale token")
    check("--text-body" in admin_css_check["markers"], "admin css deployment should include body text scale token")
    check("--text-stat" in admin_css_check["markers"], "admin css deployment should include metric text scale token")
    check("finishReviewDecision" in admin_check["markers"], "admin deployment should include sequential review marker")
    check("Campo más pendiente" in admin_check["markers"], "admin deployment should include top pending field marker")
    check("Fichas pendientes" in admin_check["markers"], "admin deployment should include next profile marker")
    check("Siguiente especialistas" in admin_check["markers"], "admin deployment should include specialist next action marker")
    check("Web pública" in admin_check["markers"], "admin deployment should include public-health marker")
    check("Caso prioritario" in admin_check["markers"], "admin deployment should include priority case marker")
    check("openPriorityReviewBtn" in admin_check["markers"], "admin deployment should include priority button marker")
    check("openClinicGroupBtn" in admin_check["markers"], "admin deployment should include clinic-group button marker")
    check("data-review-duplicate" in admin_check["markers"], "admin deployment should include duplicate filter marker")
    check("openDuplicateReviewBtn" in admin_check["markers"], "admin deployment should include duplicate open button marker")
    check("claimTraceText" in admin_check["markers"], "admin deployment should include claim traceability marker")
    check("Sin claims bloqueantes pendientes" in admin_check["markers"], "admin deployment should include blocking-claim validation marker")
    check("restoreChangeText" in admin_check["markers"], "admin deployment should include rollback preview marker")
    print("OK production health: report is read-only")


if __name__ == "__main__":
    main()
