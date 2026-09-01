#!/usr/bin/env python3
"""Read-only release-readiness report for local Vitalarga changes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import check_production_health


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://www.vitalarga.com"

SOURCE_MARKERS = [
    ("admin review queue state", "admin/index.html", 'id="reviewListPanel"'),
    ("admin clinic-centered review", "admin/index.html", 'id="reviewClinicPanel"'),
    ("admin proposal focus", "admin/index.html", 'id="reviewProposalFocus"'),
    ("admin review auto-advance", "admin/index.html", "function finishReviewDecision"),
    ("admin approve action", "admin/index.html", 'id="reviewApproveBtn"'),
    ("admin reject action", "admin/index.html", 'id="reviewRejectBtn"'),
    ("admin modify action", "admin/index.html", 'id="reviewModifyBtn"'),
    ("admin collapsible sidebar", "admin/index.html", 'id="sidebarToggleBtn"'),
    ("admin review source handoff", "admin/index.html", 'id="reviewSourceJobPanel"'),
    ("admin review source origin", "admin/index.html", 'id="reviewSourceOrigin"'),
    ("admin source-only origin warning", "admin/index.html", "Fuente sin contexto de tarea"),
    ("admin internal clinic contact", "admin/index.html", 'id="clinicInternalContactName"'),
    ("admin local version pill", "admin/index.html", 'id="localVersionPill"'),
    ("admin manual review context", "admin/index.html", 'id="clinicManualReviewContext"'),
    ("admin manual review source handoff", "admin/index.html", 'id="clinicManualReviewSourceBtn"'),
    ("admin manual review scoped source", "admin/index.html", "function reviewSourceJobTargets"),
    ("admin source job scope metadata", "admin/index.html", "target_scope: sourceJob.targetScope"),
    ("admin manual review field focus", "admin/index.html", "openReviewManualField(button.getAttribute(\"data-review-manual-field\"));"),
    ("admin manual review direct entry", "admin/index.html", "function openReviewEntry"),
    ("admin review next-card panel", "admin/index.html", 'id="reviewSelectionOpenBtn"'),
    ("admin review next-card renderer", "admin/index.html", "function renderReviewQueueSelection"),
    ("admin manual review wording", "admin/index.html", "Revisión manual de fichas"),
    ("admin compact priority filter", "admin/index.html", "Prioridad: todas"),
    ("admin bounded source intent", "admin/index.html", "function reviewSourceJobOperatorIntent"),
    ("admin visual scale tokens", "admin/admin.css", "--text-ui"),
    ("admin non-flat review columns", "admin/admin.css", "minmax(0, 1fr) minmax(260px, 320px)"),
    ("LLM manual review context", "scripts/review_proposal_decision_packets.py", "manual_review_context"),
    ("LLM manual source scope", "scripts/review_proposal_decision_packets.py", "primary_target_first"),
    ("LLM Google reviews dependency", "scripts/review_proposal_decision_packets.py", '"approval_dependency"'),
    ("LLM Google reviews suggestion guard", "scripts/validate_review_decision_suggestion.py", "google_reviews_dependency_errors"),
    ("LLM source origin status", "scripts/review_proposal_decision_packets.py", "source_origin_status"),
    ("LLM prompt source origin status", "scripts/prepare_review_decision_llm_prompt.py", '"source_origin_status"'),
    ("LLM bounded source intent", "scripts/review_proposal_decision_packets.py", "operator_requested_field_summary"),
    ("source worker LLM boundary", "scripts/process_extract_clinic_profile_jobs.py", "llm_boundary"),
    ("LLM source-origin digest status", "scripts/admin_digest.py", "source_origin_audit_status"),
    ("LLM source-origin global status", "scripts/global_plan_status.py", "Preparación LLM de revisiones"),
    ("LLM source-context audit labels", "scripts/audit_review_source_job_context.py", "listo para LLM"),
    ("logo asset guard in build", "build.py", "def _looks_like_logo_asset"),
    ("logo download guard", "scripts/fetch_logos.py", "def looks_like_image"),
]

DIST_MARKERS = [
    ("built admin clinic-centered review", "dist/admin/index.html", "reviewClinicPanel"),
    ("built admin decision actions", "dist/admin/index.html", "reviewApproveBtn"),
    ("built admin review source origin", "dist/admin/index.html", "reviewSourceOrigin"),
    ("built admin source-only origin warning", "dist/admin/index.html", "Fuente sin contexto de tarea"),
    ("built admin local version pill", "dist/admin/index.html", "localVersionPill"),
    ("built admin manual review context", "dist/admin/index.html", "clinicManualReviewContext"),
    ("built admin manual review source handoff", "dist/admin/index.html", "clinicManualReviewSourceBtn"),
    ("built admin manual review scoped source", "dist/admin/index.html", "function reviewSourceJobTargets"),
    ("built admin source job scope metadata", "dist/admin/index.html", "target_scope: sourceJob.targetScope"),
    ("built admin manual review field focus", "dist/admin/index.html", "openReviewManualField(button.getAttribute(\"data-review-manual-field\"));"),
    ("built admin manual review direct entry", "dist/admin/index.html", "function openReviewEntry"),
    ("built admin review next-card panel", "dist/admin/index.html", 'id="reviewSelectionOpenBtn"'),
    ("built admin review next-card renderer", "dist/admin/index.html", "function renderReviewQueueSelection"),
    ("built admin compact priority filter", "dist/admin/index.html", "Prioridad: todas"),
    ("built admin bounded source intent", "dist/admin/index.html", "function reviewSourceJobOperatorIntent"),
    ("built admin visual scale tokens", "dist/admin/admin.css", "--text-ui"),
    ("built admin non-flat review columns", "dist/admin/admin.css", "minmax(0, 1fr) minmax(260px, 320px)"),
    ("built Tiara profile remains", "dist/clinica/tiara-health/index.html", "Tiara Health"),
]

ABSENT_PATHS = [
    ("invalid Tiara source logo", "assets/logos/orig/tiara-health.svg"),
    ("invalid Tiara thumb logo", "assets/logos/thumb/tiara-health.svg"),
    ("built invalid Tiara source logo", "dist/assets/logos/orig/tiara-health.svg"),
    ("built invalid Tiara thumb logo", "dist/assets/logos/thumb/tiara-health.svg"),
]


def run_git(args: list[str], root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def git_text(args: list[str], root: Path = ROOT) -> str:
    result = run_git(args, root)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def git_lines(args: list[str], root: Path = ROOT) -> list[str]:
    text = git_text(args, root)
    return [line for line in text.splitlines() if line.strip()]


def ahead_behind(upstream: str, root: Path = ROOT) -> dict[str, int] | None:
    if not upstream:
        return None
    counts = git_text(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"], root).split()
    if len(counts) != 2:
        return None
    try:
        return {"behind": int(counts[0]), "ahead": int(counts[1])}
    except ValueError:
        return None


def git_summary(root: Path = ROOT, limit: int = 8) -> dict[str, Any]:
    upstream = git_text(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root)
    divergence = ahead_behind(upstream, root)
    if upstream:
        recent = git_lines(["log", "--oneline", f"{upstream}..HEAD", f"--max-count={limit}"], root)
    else:
        recent = git_lines(["log", "--oneline", f"--max-count={limit}"], root)
    status = git_lines(["status", "--short"], root)
    return {
        "branch": git_text(["rev-parse", "--abbrev-ref", "HEAD"], root),
        "commit": git_text(["rev-parse", "--short", "HEAD"], root),
        "commit_subject": git_text(["log", "-1", "--pretty=%s"], root),
        "upstream": upstream,
        "ahead": divergence["ahead"] if divergence else None,
        "behind": divergence["behind"] if divergence else None,
        "uncommitted_changes": status,
        "recent_local_commits": recent,
    }


def file_contains(root: Path, relative_path: str, marker: str) -> dict[str, Any]:
    path = root / relative_path
    if not path.exists():
        return {"path": relative_path, "marker": marker, "ok": None, "detail": "archivo no generado"}
    body = path.read_text(encoding="utf-8", errors="replace")
    return {"path": relative_path, "marker": marker, "ok": marker in body, "detail": ""}


def marker_check(root: Path, name: str, relative_path: str, marker: str) -> dict[str, Any]:
    result = file_contains(root, relative_path, marker)
    result["name"] = name
    result["kind"] = "marker"
    return result


def absent_path_check(root: Path, name: str, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    if relative_path.startswith("dist/") and not (root / "dist").exists():
        return {"name": name, "kind": "absent_path", "path": relative_path, "ok": None, "detail": "dist no generado"}
    return {
        "name": name,
        "kind": "absent_path",
        "path": relative_path,
        "ok": not path.exists(),
        "detail": "debe estar ausente",
    }


def logo_status_check(root: Path) -> dict[str, Any]:
    path = root / "assets/logos/status.json"
    if not path.exists():
        return {"name": "Tiara logo status", "kind": "json", "path": str(path.relative_to(root)), "ok": None, "detail": "sin status"}
    status = json.loads(path.read_text(encoding="utf-8"))
    tiara = status.get("tiara-health") if isinstance(status, dict) else {}
    ok = isinstance(tiara, dict) and tiara.get("ok") is False and "no parece un logo" in str(tiara.get("error") or "")
    return {
        "name": "Tiara logo status",
        "kind": "json",
        "path": "assets/logos/status.json",
        "ok": ok,
        "detail": str(tiara.get("error") or "") if isinstance(tiara, dict) else "formato inesperado",
    }


def run_local_artifact_checks(root: Path = ROOT) -> list[dict[str, Any]]:
    checks = [marker_check(root, *item) for item in SOURCE_MARKERS]
    checks.extend(marker_check(root, *item) for item in DIST_MARKERS)
    checks.extend(absent_path_check(root, *item) for item in ABSENT_PATHS)
    checks.append(logo_status_check(root))
    return checks


def checks_ok(checks: list[dict[str, Any]]) -> bool:
    return all(item.get("ok") is not False for item in checks)


def production_marker_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return {"checked": False, "ok": None, "attention": []}
    attention = [
        {
            "name": item.get("name"),
            "url": item.get("url"),
            "status": item.get("status"),
            "missing_markers": item.get("missing_markers") or [],
            "error": item.get("error") or "",
        }
        for item in report.get("checks") or []
        if not item.get("ok")
    ]
    return {"checked": True, "ok": report.get("ok") is True, "attention": attention}


def run_release_readiness(
    root: Path = ROOT,
    include_production: bool = False,
    production_base_url: str = DEFAULT_BASE_URL,
    production_timeout: int = 12,
    commit_limit: int = 8,
) -> dict[str, Any]:
    local_checks = run_local_artifact_checks(root)
    production_report = (
        check_production_health.run_checks(production_base_url, production_timeout)
        if include_production
        else None
    )
    git = git_summary(root, commit_limit)
    production = production_marker_summary(production_report)
    local_ready = checks_ok(local_checks) and not git["uncommitted_changes"]
    production_ready = production["ok"] is True if production["checked"] else None
    return {
        "ok": local_ready and (production_ready is not False),
        "writes_data": False,
        "pushes_or_deploys": False,
        "git": git,
        "local_ready": local_ready,
        "local_checks": local_checks,
        "production": production,
    }


def state_label(value: bool | None) -> str:
    if value is True:
        return "OK"
    if value is False:
        return "Atención"
    return "No comprobado"


def daniel_reading(report: dict[str, Any]) -> list[str]:
    git = report.get("git") or {}
    production = report.get("production") or {}
    uncommitted = git.get("uncommitted_changes") or []
    lines: list[str] = []

    if uncommitted:
        lines.append(f"Hay {len(uncommitted)} cambio(s) sin commit: están solo en este worktree.")
    elif report.get("local_ready"):
        lines.append("Los cambios están preparados en local y la build generada contiene los marcadores esperados.")
    else:
        lines.append("El estado local necesita revisión antes de pensar en publicar.")

    upstream = git.get("upstream")
    ahead = git.get("ahead")
    if not upstream:
        lines.append("Este worktree no tiene upstream configurado: trátalo como local hasta que Daniel autorice push y despliegue.")
    elif ahead:
        lines.append(f"Hay {ahead} commit(s) locales pendientes de push: no pueden darse por online.")
    else:
        lines.append("Git no muestra commits locales pendientes frente al upstream actual.")

    if not production.get("checked"):
        lines.append("Producción no se ha comprobado en esta ejecución: no hay prueba de que estos cambios estén online.")
    elif production.get("ok"):
        lines.append("La web pública respondió a las comprobaciones, pero eso no sustituye la autorización de publicación.")
    else:
        lines.append("La web pública necesita atención: faltan marcadores o hubo error de comprobación.")

    lines.append("Este informe no publica, no hace push y no toca datos.")
    return lines


def format_report(report: dict[str, Any]) -> str:
    git = report.get("git") or {}
    production = report.get("production") or {}
    lines = [
        "# Vitalarga release readiness",
        "",
        f"Estado local: {state_label(report.get('local_ready'))}",
        f"Producción: {state_label(production.get('ok')) if production.get('checked') else 'No comprobada'}",
        "- Writes data: no",
        "- Push/deploy: no",
        f"- Rama: {git.get('branch') or 'desconocida'}",
        f"- Commit local: {git.get('commit') or 'desconocido'} {git.get('commit_subject') or ''}".rstrip(),
    ]
    upstream = git.get("upstream")
    if upstream:
        lines.append(f"- Upstream: {upstream}")
        lines.append(f"- Commits locales pendientes de push: {git.get('ahead', 0)}")
        lines.append(f"- Commits remotos pendientes de integrar: {git.get('behind', 0)}")
    else:
        lines.append("- Upstream: no configurado en este worktree")
    uncommitted = git.get("uncommitted_changes") or []
    lines.append(f"- Cambios sin commit: {'sí (' + str(len(uncommitted)) + ')' if uncommitted else 'no'}")
    lines.extend(["", "## Lectura para Daniel"])
    lines.extend(f"- {line}" for line in daniel_reading(report))
    lines.extend(["", "## Comprobaciones locales"])
    for item in report.get("local_checks") or []:
        state = state_label(item.get("ok"))
        detail = f" · {item.get('detail')}" if item.get("detail") else ""
        lines.append(f"- {item.get('name')}: {state} · {item.get('path')}{detail}")
    lines.extend(["", "## Commits locales recientes"])
    recent = git.get("recent_local_commits") or []
    if recent:
        lines.extend(f"- {line}" for line in recent[:8])
    else:
        lines.append("- No hay commits locales pendientes según el upstream actual.")
    lines.extend(["", "## Producción"])
    if not production.get("checked"):
        lines.append("- No comprobada. Usa `--production-health` para mirar la web pública sin publicar nada.")
    elif production.get("ok"):
        lines.append("- La web pública contiene los marcadores esperados.")
    else:
        lines.append("- La web pública no contiene todos los marcadores esperados.")
        for item in production.get("attention") or []:
            missing = item.get("missing_markers") or []
            status = item.get("status") if item.get("status") is not None else "sin respuesta"
            if item.get("error"):
                detail = "error: " + str(item.get("error"))[:160]
            elif missing:
                sample = ", ".join(missing[:8])
                suffix = "..." if len(missing) > 8 else ""
                detail = "faltan: " + sample + suffix
            else:
                detail = "revisar"
            lines.append(f"- {item.get('name')}: {status} · {detail} · {item.get('url') or ''}".rstrip())
    lines.extend([
        "",
        "## Lectura rápida",
        "- Este informe no sube cambios, no publica Netlify y no edita Supabase.",
        "- Si producción no está comprobada o faltan marcadores, el cambio puede estar bien en local pero no demostrado online.",
        "- Para poner cambios online hace falta autorización explícita de Daniel.",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-health", action="store_true", help="Check the public site read-only.")
    parser.add_argument("--production-base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--production-timeout", type=int, default=12)
    parser.add_argument("--commit-limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print raw JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.production_timeout < 3 or args.production_timeout > 60:
        raise SystemExit("--production-timeout must be between 3 and 60 seconds.")
    if args.commit_limit < 1 or args.commit_limit > 50:
        raise SystemExit("--commit-limit must be between 1 and 50.")
    report = run_release_readiness(
        include_production=args.production_health,
        production_base_url=args.production_base_url,
        production_timeout=args.production_timeout,
        commit_limit=args.commit_limit,
    )
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
