#!/usr/bin/env python3
"""Checks for the read-only production health report."""

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
    admin_check = [item for item in CHECKS if item["name"] == "admin_shell"][0]
    check("Duplicados mejoras" in admin_check["markers"], "admin deployment should include review-backlog marker")
    check("Web pública" in admin_check["markers"], "admin deployment should include public-health marker")
    print("OK production health: report is read-only")


if __name__ == "__main__":
    main()
