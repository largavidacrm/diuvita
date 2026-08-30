#!/usr/bin/env python3
"""Checks for the read-only production health report."""

import check_production_health as health
from check_production_health import CHECKS, check_response, clean_base_url, format_report


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    ok_item = check_response("home", "https://example.test/", 200, "Diuvita Buscar clínica", ["Diuvita"])
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
    check("# Diuvita production health" in output, "title missing")
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
    home_check = [item for item in CHECKS if item["name"] == "home"][0]
    profile_check = [item for item in CHECKS if item["name"] == "public_profile_ux"][0]
    check("card-signals" in home_check["markers"], "home deployment should include card signal marker")
    check("profile-snapshot" in profile_check["markers"], "profile deployment should include summary stats marker")
    check("Duplicados mejoras" in admin_check["markers"], "admin deployment should include review-backlog marker")
    check("Grupo por clínica" in admin_check["markers"], "admin deployment should include clinic workgroup marker")
    check("Primer atasco" in admin_check["markers"], "admin deployment should include first backlog target marker")
    check("Freno bandeja" in admin_check["markers"], "admin deployment should include review backlog guard marker")
    check("loadSourceCoverage" in admin_check["markers"], "admin deployment should include source coverage loader marker")
    check("Fuentes por ficha" in admin_check["markers"], "admin deployment should include source coverage marker")
    check("Fichas sin fuente" in admin_check["markers"], "admin deployment should include source gap marker")
    check("Siguiente fuente" in admin_check["markers"], "admin deployment should include next source marker")
    check("openSourceTargetBtn" in admin_check["markers"], "admin deployment should include next source button marker")
    check("Campo más pendiente" in admin_check["markers"], "admin deployment should include top pending field marker")
    check("Siguiente ficha" in admin_check["markers"], "admin deployment should include next profile marker")
    check("Siguiente especialistas" in admin_check["markers"], "admin deployment should include specialist next action marker")
    check("Web pública" in admin_check["markers"], "admin deployment should include public-health marker")
    check("Caso prioritario" in admin_check["markers"], "admin deployment should include priority case marker")
    check("openPriorityReviewBtn" in admin_check["markers"], "admin deployment should include priority button marker")
    check("openClinicGroupBtn" in admin_check["markers"], "admin deployment should include clinic-group button marker")
    check("reviewFlowPanel" in admin_check["markers"], "admin deployment should include publication-flow marker")
    check("data-review-duplicate" in admin_check["markers"], "admin deployment should include duplicate filter marker")
    check("openDuplicateReviewBtn" in admin_check["markers"], "admin deployment should include duplicate open button marker")
    check("relatedReviewsPanel" in admin_check["markers"], "admin deployment should include related-review marker")
    check("claimTraceText" in admin_check["markers"], "admin deployment should include claim traceability marker")
    check("Sin claims bloqueantes pendientes" in admin_check["markers"], "admin deployment should include blocking-claim validation marker")
    check("restoreChangeText" in admin_check["markers"], "admin deployment should include rollback preview marker")
    print("OK production health: report is read-only")


if __name__ == "__main__":
    main()
