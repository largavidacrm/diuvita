#!/usr/bin/env python3
"""Print a plain-Spanish global roadmap status for Vitalarga."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

from admin_digest import (
    as_int,
    first_clinic_workgroup,
    google_link_review_status,
    location_coverage_status,
    load_digest,
    maturity_blockers,
    next_action_label,
    next_profile_action,
    next_portal_action,
    next_source_action,
    next_specialist_action,
    parse_timestamp,
    portal_pending_total,
    portal_status,
    publication_control_status,
    review_backlog_guard_status,
    source_coverage_status,
    specialist_review_status,
    top_pending_profile_field,
)
from daniel_review_brief import next_clicks
from submit_discovery_candidates import get_default_admin_email, load_env_file


def git_label() -> str:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "no disponible"
    if branch and commit:
        return f"{branch} · {commit}"
    return commit or branch or "no disponible"


def source_monitoring_status(digest: dict[str, Any]) -> str:
    monitoring = digest.get("source_monitoring") or {}
    due = as_int(monitoring.get("due_sources"))
    if due:
        return f"{due} fuentes pendientes de revisar"
    next_due = parse_timestamp(monitoring.get("next_due_at"))
    if next_due != "-":
        return f"todo reciente; próxima revisión {next_due}"
    return "sin próxima revisión medida"


def automation_status(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    automation = summary.get("automation") or {}
    shadow = "modo sombra activo" if automation.get("shadow_mode_active") else "modo sombra inactivo"
    publish = "auto-publicación activa" if automation.get("auto_publish_enabled") else "auto-publicación apagada"
    return f"{shadow}; {publish}"


def visible_clinic_status(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    clinics = summary.get("clinics") or {}
    published = as_int(clinics.get("published"))
    preliminary = as_int(clinics.get("preliminary"))
    return f"{published} publicadas y {preliminary} preliminares"


def specialist_status(digest: dict[str, Any]) -> str:
    coverage = digest.get("specialist_coverage") or {}
    visible = as_int(coverage.get("visible_clinics"))
    with_specialists = as_int(coverage.get("with_specialists"))
    without_specialists = as_int(coverage.get("without_specialists"))
    if not visible:
        return "sin fichas visibles medidas"
    return f"{with_specialists}/{visible} fichas con especialistas; {without_specialists} pendientes"


def location_status(digest: dict[str, Any]) -> str:
    return location_coverage_status(digest)


def plan_phase(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    jobs = summary.get("jobs") or {}
    reviews = summary.get("reviews") or {}
    failed_jobs = as_int(jobs.get("failed")) + as_int(jobs.get("dead_letter"))
    open_reviews = as_int(reviews.get("open"))
    if failed_jobs:
        return "estabilización técnica"
    if portal_pending_total(digest):
        return "portal de clínicas y validación manual"
    if open_reviews >= 45:
        return "centro de control y reducción de bandeja"
    return "centro de control, trazabilidad y ciclo sombra"


def daniel_now_status(digest: dict[str, Any]) -> str:
    group = first_clinic_workgroup(digest)
    if group != "sin grupo por clínica medido":
        return group
    action = next_action_label(digest)
    if action != "Sin accion urgente":
        return action
    profile = next_profile_action(digest)
    if profile != "sin ficha pendiente medida":
        return profile
    return "sin acción urgente medida"


def codex_can_continue_status(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    reviews = summary.get("reviews") or {}
    jobs = summary.get("jobs") or {}
    open_reviews = as_int(reviews.get("open"))
    failed_jobs = as_int(jobs.get("failed")) + as_int(jobs.get("dead_letter"))
    source_coverage = digest.get("source_coverage") or {}
    specialist_coverage = digest.get("specialist_coverage") or {}
    specialist_reviews = digest.get("specialist_reviews") or {}
    profile_completeness = digest.get("profile_completeness") or {}

    if failed_jobs:
        return "resolver fallos técnicos y volver a medir"
    if open_reviews >= 45:
        return "mejorar panel, extractores y checks sin crear tarjetas nuevas"
    if as_int(source_coverage.get("clinics_needing_source_work")):
        return "mejorar trazabilidad de fuentes y propuestas internas"
    if as_int(specialist_reviews.get("open_count")):
        return "mejorar revisión de especialistas propuestos sin publicarlos"
    if as_int(specialist_coverage.get("without_specialists")):
        return "priorizar páginas de equipo para especialistas publicados"
    if as_int(profile_completeness.get("pending_google_maps")):
        return "preparar revisión de Google Maps de clínica"
    return "preparar el siguiente bloque técnico sin publicar"


def not_ready_status(digest: dict[str, Any]) -> str:
    blockers = maturity_blockers(digest)
    if blockers:
        return blockers[0]
    return "auto-publicación y growth quedan parados hasta decisión explícita de Daniel"


def format_global_plan_status(digest: dict[str, Any], git_ref: str = "") -> str:
    summary = digest.get("summary") or {}
    reviews = summary.get("reviews") or {}
    blockers = maturity_blockers(digest)
    output = [
        "# Vitalarga: estado del plan global",
        "",
        f"Generado: {parse_timestamp(digest.get('generated_at') or summary.get('generated_at'))}",
        f"Git: {git_ref or 'no comprobado'}",
        "",
        "## Lectura rápida",
        f"- Daniel ahora: {daniel_now_status(digest)}.",
        f"- Codex puede seguir con: {codex_can_continue_status(digest)}.",
        f"- No activar todavía: {not_ready_status(digest)}.",
        "",
        "## Siguiente en el panel",
        *[f"- {item}" for item in next_clicks(digest)],
        "",
        "## Dónde estamos",
        f"- Fase activa: {plan_phase(digest)}.",
        f"- Web pública: {visible_clinic_status(digest)}.",
        f"- Supervisión: {automation_status(digest)}.",
        f"- Bandeja: {as_int(reviews.get('open'))} revisiones abiertas; {review_backlog_guard_status(digest)}.",
        "",
        "## Carriles del plan",
        "- Centro de control: operativo; Daniel puede revisar, editar, publicar manualmente y ver prioridades.",
        f"- Trazabilidad de fuentes: {source_coverage_status(digest)}.",
        f"- Sedes y ubicaciones: {location_status(digest)}.",
        f"- Ciclo autónomo: activo en sombra; señal automática base: {next_action_label(digest)}.",
        f"- Monitorización: {source_monitoring_status(digest)}.",
        f"- Coste Netlify: publicación {publication_control_status(digest)}.",
        f"- Portal clínicas: {portal_status(digest)}.",
        f"- Knowledge graph clínico: {specialist_status(digest)}.",
        "- Growth/SEO/outreach: pendiente hasta que la precisión y la bandeja estén más maduras.",
        "",
        "## Siguiente trabajo recomendado",
        f"- Señal automática base: {next_action_label(digest)}.",
        f"- Grupo por clínica: {first_clinic_workgroup(digest)}.",
        f"- Google Maps propuestos: {google_link_review_status(digest)}.",
        f"- Especialistas propuestos: {specialist_review_status(digest)}.",
        f"- Siguiente fuente: {next_source_action(digest)}.",
        f"- Siguiente ficha: {next_profile_action(digest)}.",
        f"- Siguiente portal: {next_portal_action(digest)}.",
        f"- Siguiente especialistas: {next_specialist_action(digest)}.",
        f"- Campo más pendiente: {top_pending_profile_field(digest)}.",
        "",
        "## Qué no está maduro aún",
    ]
    if blockers:
        output.extend(f"- {item}." for item in blockers[:5])
    else:
        output.append("- No hay bloqueos medidos para hablar de auto-publicación de bajo riesgo, pero Daniel tendría que aprobarla.")
    output.extend([
        "",
        "Nota: este informe no publica, no edita clínicas y no resuelve tarjetas.",
    ])
    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used to read the protected dashboard summary.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum open reviews and failed jobs to inspect.")
    parser.add_argument("--json", action="store_true", help="Print raw digest JSON instead of the readable status.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    digest = load_digest(admin_email, args.limit, local_env)
    if args.json:
        print(json.dumps(digest, ensure_ascii=False, indent=2))
    else:
        print(format_global_plan_status(digest, git_label()), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
