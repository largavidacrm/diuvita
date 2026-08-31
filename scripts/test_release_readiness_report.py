#!/usr/bin/env python3
"""Checks for the read-only release readiness report."""

from pathlib import Path

import release_readiness_report as release


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    local_checks = release.run_local_artifact_checks(ROOT)
    check(any(item["name"] == "admin clinic-centered review" for item in local_checks), "admin review marker missing")
    check(any(item["name"] == "admin collapsible sidebar" for item in local_checks), "admin sidebar marker missing")
    check(any(item["name"] == "admin review source handoff" for item in local_checks), "admin source handoff marker missing")
    check(any(item["name"] == "admin internal clinic contact" for item in local_checks), "admin internal contact marker missing")
    check(any(item["name"] == "admin manual review context" for item in local_checks), "admin manual review context marker missing")
    check(any(item["name"] == "admin manual review field focus" for item in local_checks), "admin manual review field-focus marker missing")
    check(any(item["name"] == "admin manual review wording" for item in local_checks), "admin manual review wording marker missing")
    check(any(item["name"] == "admin compact priority filter" for item in local_checks), "admin priority filter marker missing")
    check(any(item["name"] == "admin visual scale tokens" for item in local_checks), "admin visual scale marker missing")
    check(any(item["name"] == "LLM manual review context" for item in local_checks), "LLM manual review marker missing")
    check(any(item["name"] == "built admin manual review context" for item in local_checks), "built admin manual review marker missing")
    check(any(item["name"] == "built admin manual review field focus" for item in local_checks), "built admin field-focus marker missing")
    check(any(item["name"] == "built admin compact priority filter" for item in local_checks), "built admin priority filter marker missing")
    check(any(item["name"] == "built admin visual scale tokens" for item in local_checks), "built admin visual scale marker missing")
    check(any(item["name"] == "logo asset guard in build" for item in local_checks), "build logo guard marker missing")
    check(any(item["name"] == "Tiara logo status" and item["ok"] is True for item in local_checks), "Tiara logo status should be guarded")
    check(all(item["ok"] is not False for item in local_checks), "local artifact checks should pass")

    original_git_text = release.git_text
    original_git_lines = release.git_lines
    try:
        def fake_git_text(args, root=ROOT):
            command = " ".join(args)
            values = {
                "rev-parse --abbrev-ref --symbolic-full-name @{u}": "origin/codex/imda-source-extraction",
                "rev-list --left-right --count origin/codex/imda-source-extraction...HEAD": "0 2",
                "rev-parse --abbrev-ref HEAD": "codex/imda-source-extraction",
                "rev-parse --short HEAD": "abc1234",
                "log -1 --pretty=%s": "Example local change",
                "log --oneline origin/codex/imda-source-extraction..HEAD --max-count=8": "abc1234 Example local change\nbcd2345 Previous local change",
                "status --short": "",
            }
            return values.get(command, "")

        def fake_git_lines(args, root=ROOT):
            return [line for line in fake_git_text(args, root).splitlines() if line.strip()]

        release.git_text = fake_git_text
        release.git_lines = fake_git_lines
        report = release.run_release_readiness(root=ROOT, include_production=False)
    finally:
        release.git_text = original_git_text
        release.git_lines = original_git_lines

    output = release.format_report(report)
    check(report["writes_data"] is False, "release report must be read-only")
    check(report["pushes_or_deploys"] is False, "release report must not push or deploy")
    check(report["git"]["ahead"] == 2, "local commits ahead should be counted")
    check(report["local_ready"] is True, "clean local fixtures should be ready")
    check("Producción: No comprobada" in output, "production should be explicit when omitted")
    check("Push/deploy: no" in output, "report should say it does not deploy")
    check("Commits locales pendientes de push: 2" in output, "ahead count missing")
    check("Para poner cambios online hace falta autorización explícita de Daniel." in output, "Daniel approval boundary missing")

    production = {
        "ok": False,
        "checks": [
            {"name": "admin_shell", "url": "https://example.test/admin/", "ok": False, "status": 200, "missing_markers": ["reviewClinicPanel"], "error": ""},
        ],
    }
    production_summary = release.production_marker_summary(production)
    check(production_summary["checked"] is True, "production summary should mark checked")
    check(production_summary["ok"] is False, "production missing marker should need attention")
    check(production_summary["attention"][0]["missing_markers"] == ["reviewClinicPanel"], "missing production marker should be preserved")
    check(production_summary["attention"][0]["url"] == "https://example.test/admin/", "production URL should be preserved")

    report["production"] = production_summary
    production_output = release.format_report(report)
    check("admin_shell: 200 · faltan: reviewClinicPanel · https://example.test/admin/" in production_output, "production detail should include status and URL")

    report["production"] = {
        "checked": True,
        "ok": False,
        "attention": [{"name": "home", "url": "https://example.test/", "status": None, "missing_markers": ["Vitalarga"], "error": "DNS blocked"}],
    }
    error_output = release.format_report(report)
    check("home: sin respuesta · error: DNS blocked · https://example.test/" in error_output, "network errors should be clearer than missing markers")
    print("OK release readiness: local vs production state is reported safely")


if __name__ == "__main__":
    main()
