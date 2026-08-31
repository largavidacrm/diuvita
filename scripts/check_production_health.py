#!/usr/bin/env python3
"""Read-only production health check for Vitalarga public URLs."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://www.vitalarga.com"
MAX_RESPONSE_BYTES = 2_000_000

CHECKS = [
    {
        "name": "home",
        "path": "/",
        "markers": ["Vitalarga", "Buscar clínica", 'class="results-section"', 'class="logo-link"', "card-signals"],
    },
    {
        "name": "admin_shell",
        "path": "/admin/",
        "markers": [
            "Centro de control",
            "loadProfileCompleteness",
            "loadSourceCoverage",
            "Fichas completas",
            "Campo más pendiente",
            "Fichas pendientes",
            "Fuentes por ficha",
            "Fichas sin fuente",
            "Siguiente fuente",
            "openSourceTargetBtn",
            "Plan global",
            "globalPlanPanel",
            "globalPlanOpenNextBtn",
            "loadPublicationControl",
            "Publicación agrupada",
            "reviewDecisionSummary",
            "reviewCurrentRelevantPanel",
            "reviewClinicPanel",
            "reviewProposalFocus",
            "reviewEvidencePanel",
            "reviewSourceOrigin",
            "reviewWarningPanel",
            "reviewApproveBtn",
            "reviewRejectBtn",
            "reviewModifyBtn",
            "sidebarToggleBtn",
            "reviewSourceJobPanel",
            "clinicInternalContactName",
            "clinicManualReviewSourceBtn",
            "createReviewSourceJobFor",
            "reviewSourceJobTargets",
            "target_scope: sourceJob.targetScope",
            "firstReviewMissingFieldTargetId",
            "Prioridad: todas",
            "finishReviewDecision",
            "Siguiente especialistas",
            "Duplicados mejoras",
            "Contexto de grupo",
            "Primer atasco",
            "Freno bandeja",
            "Web pública",
            "Caso prioritario",
            "openPriorityReviewBtn",
            "openClinicGroupBtn",
            "data-review-duplicate",
            "openDuplicateReviewBtn",
            "claimTraceText",
            "Sin claims bloqueantes pendientes",
            "restoreChangeText",
        ],
    },
    {
        "name": "admin_css",
        "path": "/admin/admin.css",
        "markers": ["--text-ui", "--text-body", "--text-stat"],
    },
    {
        "name": "public_profile_ux",
        "path": "/clinica/the-long-game/",
        "markers": ["profile-jump", "location-list", "Sedes y acceso", "Especialistas publicados por la clínica"],
    },
    {
        "name": "sitemap",
        "path": "/sitemap.xml",
        "markers": ["/clinica/"],
    },
    {
        "name": "favicon",
        "path": "/favicon.svg",
        "markers": ["<svg", 'viewBox="0 0 64 64"', "#0E4F4A"],
    },
]


def clean_base_url(value: str) -> str:
    base = str(value or DEFAULT_BASE_URL).strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        raise SystemExit("--base-url must start with http:// or https://")
    return base


def fetch_text(url: str, timeout: int) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "VitalargaHealthCheck/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", response.getcode()))
        body = response.read(MAX_RESPONSE_BYTES)
    return status, body.decode("utf-8", errors="replace")


def check_response(name: str, url: str, status: int | None, body: str, markers: list[str], error: str = "") -> dict[str, Any]:
    missing = [marker for marker in markers if marker not in body]
    return {
        "name": name,
        "url": url,
        "status": status,
        "ok": not error and status is not None and status < 400 and not missing,
        "missing_markers": missing,
        "error": error,
    }


def run_checks(base_url: str, timeout: int) -> dict[str, Any]:
    base = clean_base_url(base_url)
    results = []
    for check in CHECKS:
        url = base + check["path"]
        try:
            status, body = fetch_text(url, timeout)
            results.append(check_response(check["name"], url, status, body, check["markers"]))
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            results.append(check_response(check["name"], url, None, "", check["markers"], str(exc)))
    return {
        "base_url": base,
        "ok": all(item["ok"] for item in results),
        "checks": results,
        "writes_data": False,
    }


def run_checks_with_retries(base_url: str, timeout: int, retries: int = 0, retry_delay: int = 10) -> dict[str, Any]:
    attempts = 0
    report = run_checks(base_url, timeout)
    attempts += 1
    while not report["ok"] and attempts <= retries:
        time.sleep(retry_delay)
        report = run_checks(base_url, timeout)
        attempts += 1
    report["attempts"] = attempts
    report["retries"] = retries
    report["retry_delay_seconds"] = retry_delay
    return report


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "# Vitalarga production health",
        "",
        f"Base: {report.get('base_url')}",
        f"Estado: {'OK' if report.get('ok') else 'Atención'}",
        "- Writes data: no",
        f"- Attempts: {report.get('attempts', 1)}",
        "",
        "## Checks",
    ]
    for item in report.get("checks") or []:
        status = item.get("status") if item.get("status") is not None else "sin respuesta"
        state = "OK" if item.get("ok") else "Atención"
        detail = ""
        if item.get("missing_markers"):
            detail = " · faltan: " + ", ".join(item["missing_markers"])
        if item.get("error"):
            detail = " · error: " + str(item["error"])[:160]
        lines.append(f"- {item.get('name')}: {state} · {status} · {item.get('url')}{detail}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--retries", type=int, default=0, help="Retry failed checks this many times.")
    parser.add_argument("--retry-delay", type=int, default=10, help="Seconds to wait between retries.")
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout < 3 or args.timeout > 60:
        raise SystemExit("--timeout must be between 3 and 60 seconds.")
    if args.retries < 0 or args.retries > 5:
        raise SystemExit("--retries must be between 0 and 5.")
    if args.retry_delay < 1 or args.retry_delay > 120:
        raise SystemExit("--retry-delay must be between 1 and 120 seconds.")
    report = run_checks_with_retries(args.base_url, args.timeout, args.retries, args.retry_delay)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report), end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
