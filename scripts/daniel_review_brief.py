#!/usr/bin/env python3
"""Print a plain-Spanish, read-only review brief for Daniel."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import (
    as_int,
    first_backlog_bottleneck,
    first_clinic_workgroup,
    google_link_review_status,
    load_digest,
    next_action_label,
    next_profile_action,
    next_source_action,
    next_specialist_action,
    parse_timestamp,
    review_backlog_guard_status,
    source_coverage_status,
    specialist_review_status,
    top_pending_profile_field,
)
from check_production_health import run_checks
from submit_discovery_candidates import get_default_admin_email, load_env_file


TYPE_LABELS = {
    "blocking_claim_review": ("claim bloqueante", "claims bloqueantes"),
    "candidate_clinic": ("clínica nueva", "clínicas nuevas"),
    "clinic_profile_enrichment": ("mejora de ficha", "mejoras de ficha"),
    "source_change_detected": ("cambio de fuente", "cambios de fuente"),
    "clinic_quality_audit": ("auditoría de calidad", "auditorías de calidad"),
}


def review_counts(digest: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in digest.get("reviews_by_type") or []:
        review_type = str(item.get("review_type") or "")
        if review_type:
            counts[review_type] = as_int(item.get("open_count"))
    return counts


def review_label(review_type: str, count: int) -> str:
    labels = TYPE_LABELS.get(review_type)
    if labels:
        return labels[0] if count == 1 else labels[1]
    return review_type.replace("_", " ")


def plural(value: int, singular: str, plural_text: str) -> str:
    return singular if value == 1 else plural_text


def first_review(digest: dict[str, Any], review_type: str) -> dict[str, Any] | None:
    for item in digest.get("open_reviews") or []:
        if item.get("review_type") == review_type:
            return item
    for item in digest.get("review_examples_by_type") or []:
        if item.get("review_type") == review_type:
            return item
    return None


def review_name(item: dict[str, Any] | None, fallback_filter: str = "correspondiente") -> str:
    if not item:
        return f"abre el filtro {fallback_filter} en el panel"
    clinic = str(item.get("clinic_name") or item.get("clinic_slug") or "").strip()
    title = str(item.get("title") or "").strip()
    if clinic and title and clinic.lower() not in title.lower():
        return f"{clinic}: {title}"
    return title or clinic or "revisión abierta"


def source_status(digest: dict[str, Any]) -> str:
    monitoring = digest.get("source_monitoring") or {}
    due = as_int(monitoring.get("due_sources"))
    if due:
        return f"{due} fuentes pendientes de revisar"
    next_due = parse_timestamp(monitoring.get("next_due_at"))
    if next_due != "-":
        return f"todo reciente; próxima revisión {next_due}"
    return "sin fecha de próxima revisión"


def maturity_status(digest: dict[str, Any]) -> str:
    summary = digest.get("summary") or {}
    automation = summary.get("automation") or {}
    completed = as_int(automation.get("candidate_reviews_completed"))
    target = as_int(automation.get("shadow_review_target")) or 200
    if completed < target:
        return f"todavía faltan revisiones humanas: {completed}/{target}"
    return "lista para comentarlo con Daniel; no se activa sola"


def specialist_status(digest: dict[str, Any]) -> str:
    coverage = digest.get("specialist_coverage") or {}
    visible = as_int(coverage.get("visible_clinics"))
    with_specialists = as_int(coverage.get("with_specialists"))
    without_specialists = as_int(coverage.get("without_specialists"))
    if not visible:
        return "sin fichas visibles medidas"
    return f"{with_specialists}/{visible} fichas con especialistas; {without_specialists} pendientes"


def profile_completeness_status(digest: dict[str, Any]) -> str:
    completeness = digest.get("profile_completeness") or {}
    visible = as_int(completeness.get("visible_clinics"))
    ready = as_int(completeness.get("without_pending_fields"))
    pending = as_int(completeness.get("with_pending_fields"))
    if not visible:
        return "sin fichas visibles medidas"
    return f"{ready}/{visible} fichas sin campos pendientes medidos; {pending} con pendientes"


def review_backlog_status(digest: dict[str, Any]) -> str:
    quality = digest.get("review_backlog_quality") or {}
    duplicate_clinics = as_int(quality.get("duplicate_enrichment_clinics"))
    duplicate_reviews = as_int(quality.get("duplicate_enrichment_reviews"))
    if not duplicate_clinics:
        return "sin duplicados de mejoras detectados"
    clinic_label = "clínica" if duplicate_clinics == 1 else "clínicas"
    return f"{duplicate_clinics} {clinic_label} con varias mejoras abiertas; {duplicate_reviews} tarjetas"


def review_professionals_note(item: dict[str, Any] | None) -> str:
    count = as_int((item or {}).get("professionals_count"))
    if not count:
        return ""
    word = "especialista recogido" if count == 1 else "especialistas recogidos"
    return f" Trae {count} {word}."


def review_case_line(item: dict[str, Any] | None, fallback_filter: str) -> str:
    return f"Caso visible: {review_name(item, fallback_filter)}." + review_professionals_note(item)


def clinic_workgroup_click(digest: dict[str, Any]) -> str:
    group = digest.get("review_first_clinic_workgroup") or {}
    name = str(group.get("clinic_name") or group.get("clinic_slug") or "").strip()
    count = as_int(group.get("open_count"))
    if not name or not count:
        return ""
    return f"Pulsa Filtrar grupo y trabaja {name}: {count} tarjetas juntas."


def google_maps_click(digest: dict[str, Any]) -> str:
    status = digest.get("google_link_reviews") or {}
    count = as_int(status.get("open_count"))
    first = status.get("first_review") or {}
    if not count:
        return ""
    first_label = review_name(first, "Google Maps")
    return f"Pulsa Google Maps y valida que el enlace abre el perfil real de la clínica: {first_label}."


def specialists_click(digest: dict[str, Any]) -> str:
    status = digest.get("specialist_reviews") or {}
    count = as_int(status.get("open_count"))
    first = status.get("first_review") or {}
    total = as_int(status.get("professionals_count"))
    if not count:
        return ""
    suffix = f" En total hay {total} especialistas propuestos en la bandeja." if total else ""
    return f"Pulsa Especialistas y abre primero la tarjeta con más nombres: {review_name(first, 'Especialistas')}.{suffix}"


def next_clicks(digest: dict[str, Any]) -> list[str]:
    clicks: list[str] = []
    guard = review_backlog_guard_status(digest)
    if guard.startswith("cerca del freno") or guard.startswith("freno activo"):
        clicks.append(f"No crees trabajos nuevos hasta bajar la bandeja; ahora está {guard}.")
    for candidate in (
        clinic_workgroup_click(digest),
        specialists_click(digest),
        google_maps_click(digest),
    ):
        if candidate and candidate not in clicks:
            clicks.append(candidate)
    if not clicks:
        clicks.append("Abre el panel y usa Abrir prioridad.")
    return clicks[:4]


def production_health_status(report: dict[str, Any]) -> str:
    checks = report.get("checks") or []
    if report.get("ok"):
        return f"OK en {len(checks)} comprobaciones públicas"
    failed = [str(item.get("name") or "comprobación") for item in checks if not item.get("ok")]
    if failed:
        label = "comprobación" if len(failed) == 1 else "comprobaciones"
        return f"atención en {len(failed)} {label}: {', '.join(failed[:3])}"
    return "atención; no se pudo confirmar el estado público"


def first_step(digest: dict[str, Any]) -> list[str]:
    counts = review_counts(digest)
    failed = digest.get("recent_failed_jobs") or []
    guard = review_backlog_guard_status(digest)
    group = first_clinic_workgroup(digest)
    if failed:
        return [
            "Primero revisa fallos técnicos.",
            "Hay trabajos fallidos; conviene corregirlos antes de aceptar nuevas fichas.",
        ]
    if (guard.startswith("cerca del freno") or guard.startswith("freno activo")) and group != "sin grupo por clínica medido":
        return [
            "Primero baja un grupo repetido.",
            f"Caso visible: {group}.",
        ]
    if counts.get("blocking_claim_review"):
        return [
            "Primero revisa claims bloqueantes.",
            review_case_line(first_review(digest, "blocking_claim_review"), "Claims bloqueantes"),
        ]
    if counts.get("candidate_clinic"):
        return [
            "Primero valida clínicas nuevas.",
            review_case_line(first_review(digest, "candidate_clinic"), "Clínicas nuevas"),
        ]
    if counts.get("source_change_detected"):
        return [
            "Primero revisa cambios de fuente.",
            review_case_line(first_review(digest, "source_change_detected"), "Cambios de fuente"),
        ]
    if counts.get("clinic_profile_enrichment"):
        return [
            "Primero revisa mejoras de fichas existentes.",
            review_case_line(first_review(digest, "clinic_profile_enrichment"), "Mejoras de ficha"),
        ]
    if counts.get("clinic_quality_audit"):
        return [
            "Primero completa fichas incompletas.",
            review_case_line(first_review(digest, "clinic_quality_audit"), "Auditorías"),
        ]
    return ["No hay una acción urgente.", "Puedes revisar el panel o dejar que el sistema siga en modo sombra."]


def format_brief(digest: dict[str, Any], production_health: dict[str, Any] | None = None) -> str:
    summary = digest.get("summary") or {}
    clinics = summary.get("clinics") or {}
    reviews = summary.get("reviews") or {}
    jobs = summary.get("jobs") or {}
    automation = summary.get("automation") or {}
    counts = review_counts(digest)
    first_lines = first_step(digest)
    next_action = next_action_label(digest)
    failed_jobs = as_int(jobs.get("failed")) + as_int(jobs.get("dead_letter"))

    output = [
        "# Vitalarga: brief de revisión",
        "",
        f"Generado: {parse_timestamp(digest.get('generated_at') or summary.get('generated_at'))}",
        "",
        "## Qué mirar primero",
        f"- {first_lines[0]}",
        f"- {first_lines[1]}",
        f"- Señal automática base: {next_action}.",
        "",
        "## Próximos clics",
        *[f"- {item}" for item in next_clicks(digest)],
        "",
        "## Bandeja actual",
        f"- {as_int(reviews.get('open'))} revisiones abiertas.",
    ]

    if counts:
        for review_type in [
            "blocking_claim_review",
            "candidate_clinic",
            "source_change_detected",
            "clinic_profile_enrichment",
            "clinic_quality_audit",
        ]:
            count = counts.get(review_type)
            if count:
                output.append(
                    f"- {count} {review_label(review_type, count)} {plural(count, 'pendiente', 'pendientes')}."
                )
    else:
        output.append("- No hay tarjetas abiertas.")

    output.extend([
        "",
        "## Seguridad antes de publicar",
        f"- Auto-publicación: {'activa' if automation.get('auto_publish_enabled') else 'apagada'}.",
        f"- Modo sombra: {'activo' if automation.get('shadow_mode_active') else 'inactivo'}.",
        f"- Madurez de auto-publicación: {maturity_status(digest)}.",
        "- Crear borrador no publica. Publicar se decide después en el editor, en Validación final.",
        "",
        "## Señales técnicas",
        f"- Clínicas visibles: {as_int(clinics.get('published'))} publicadas y {as_int(clinics.get('preliminary'))} preliminares.",
        f"- Completitud de fichas: {profile_completeness_status(digest)}.",
        f"- Campo más pendiente: {top_pending_profile_field(digest)}.",
        f"- Google Maps pendientes: {google_link_review_status(digest)}.",
        f"- Siguiente ficha: {next_profile_action(digest)}.",
        f"- Especialistas publicados: {specialist_status(digest)}.",
        f"- Tarjetas con especialistas: {specialist_review_status(digest)}.",
        f"- Siguiente especialistas: {next_specialist_action(digest)}.",
        f"- Fuentes: {source_status(digest)}.",
        f"- Cobertura fuentes: {source_coverage_status(digest)}.",
        f"- Siguiente fuente: {next_source_action(digest)}.",
        f"- Bandeja: {review_backlog_status(digest)}.",
        f"- Grupo por clínica: {first_clinic_workgroup(digest)}.",
        f"- Primer atasco: {first_backlog_bottleneck(digest)}.",
        f"- Freno de bandeja: {review_backlog_guard_status(digest)}.",
        f"- Fallos técnicos abiertos: {failed_jobs}.",
    ])
    if production_health is not None:
        output.append(f"- Web pública: {production_health_status(production_health)}.")
    output.extend([
        "",
        "Panel: https://www.vitalarga.com/admin/",
    ])

    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used to read the protected dashboard summary.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum open reviews and failed jobs to inspect.")
    parser.add_argument("--json", action="store_true", help="Print raw digest JSON instead of the Daniel brief.")
    parser.add_argument("--production-health", action="store_true", help="Include a read-only public-site health line.")
    parser.add_argument("--production-base-url", default="https://www.vitalarga.com")
    parser.add_argument("--production-timeout", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.production_timeout < 3 or args.production_timeout > 60:
        raise SystemExit("--production-timeout must be between 3 and 60 seconds.")
    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    digest = load_digest(admin_email, args.limit, local_env)
    production_health = run_checks(args.production_base_url, args.production_timeout) if args.production_health else None
    if args.json:
        if production_health is not None:
            digest = dict(digest)
            digest["production_health"] = production_health
        print(json.dumps(digest, ensure_ascii=False, indent=2))
    else:
        print(format_brief(digest, production_health), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
