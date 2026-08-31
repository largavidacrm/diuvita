#!/usr/bin/env python3
"""Print a plain-Spanish, read-only review brief for Daniel."""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from admin_digest import (
    as_int,
    first_backlog_bottleneck,
    first_clinic_workgroup,
    google_link_review_status,
    load_digest,
    next_action_label,
    next_publication_action,
    next_profile_action,
    next_source_action,
    next_specialist_action,
    parse_timestamp,
    publication_control_status,
    publication_readiness_status,
    review_backlog_guard_status,
    source_coverage_status,
    specialist_review_status,
    top_publication_missing_field,
    top_pending_profile_field,
)
from check_production_health import run_checks
from submit_discovery_candidates import get_default_admin_email, load_env_file


TYPE_LABELS = {
    "blocking_claim_review": ("claim bloqueante", "claims bloqueantes"),
    "clinic_claim_request": ("reclamación de ficha", "reclamaciones de ficha"),
    "candidate_clinic": ("clínica nueva", "clínicas nuevas"),
    "clinic_profile_enrichment": ("mejora de ficha", "mejoras de ficha"),
    "source_change_detected": ("cambio de fuente", "cambios de fuente"),
    "clinic_quality_audit": ("auditoría de calidad", "auditorías de calidad"),
}
ACCOUNT_FIELD_KEYS = {"admin_email"}
ACTION_TYPE_ORDER = {
    "blocking_claim_review": 0,
    "clinic_claim_request": 1,
    "candidate_clinic": 2,
    "source_change_detected": 3,
    "clinic_profile_enrichment": 4,
    "clinic_quality_audit": 5,
}


def review_counts(digest: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in digest.get("reviews_by_type") or []:
        review_type = str(item.get("review_type") or "")
        if review_type:
            counts[review_type] = as_int(item.get("open_count"))
    return counts


def safe_json_digest(value: Any, include_account_fields: bool = False) -> Any:
    if isinstance(value, list):
        return [safe_json_digest(item, include_account_fields=include_account_fields) for item in value]
    if not isinstance(value, dict):
        return value
    clean: dict[str, Any] = {}
    for key, item in value.items():
        if not include_account_fields and str(key) in ACCOUNT_FIELD_KEYS:
            continue
        clean[key] = safe_json_digest(item, include_account_fields=include_account_fields)
    return clean


def review_label(review_type: str, count: int) -> str:
    labels = TYPE_LABELS.get(review_type)
    if labels:
        return labels[0] if count == 1 else labels[1]
    return review_type.replace("_", " ")


def normalized_review_type(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    review_type = str(item.get("review_type") or "")
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    if review_type == "clinic_quality_audit" and payload.get("quality_context") == "blocking_claims":
        return "blocking_claim_review"
    return review_type


def plural(value: int, singular: str, plural_text: str) -> str:
    return singular if value == 1 else plural_text


def first_review(digest: dict[str, Any], review_type: str) -> dict[str, Any] | None:
    for key in ("open_reviews", "sample_open_reviews", "review_examples_by_type", "sample_review_examples_by_type"):
        for item in digest.get(key) or []:
            if isinstance(item, dict) and normalized_review_type(item) == review_type:
                return item
    return None


def action_review_sort_key(item: dict[str, Any]) -> tuple[int, int]:
    review_type = normalized_review_type(item)
    priority = as_int(item.get("priority"))
    if review_type in {"blocking_claim_review", "clinic_claim_request"}:
        priority_bucket = 1000 + priority
    elif review_type == "candidate_clinic" and priority >= 90:
        priority_bucket = 900 + priority
    else:
        priority_bucket = priority
    return (-priority_bucket, ACTION_TYPE_ORDER.get(review_type, 9))


def first_action_review(digest: dict[str, Any]) -> dict[str, Any] | None:
    for source in (
        digest.get("open_reviews"),
        digest.get("sample_open_reviews"),
        digest.get("review_examples_by_type"),
        digest.get("sample_review_examples_by_type"),
    ):
        if not isinstance(source, list):
            continue
        candidates = [item for item in source if isinstance(item, dict) and normalized_review_type(item)]
        if candidates:
            return sorted(candidates, key=action_review_sort_key)[0]
    return None


def review_name(item: dict[str, Any] | None, fallback_filter: str = "correspondiente") -> str:
    if not item:
        return f"abre el filtro {fallback_filter} en el panel"
    clinic = str(item.get("clinic_name") or item.get("clinic_slug") or "").strip()
    title = review_display_title(item)
    if clinic and title and clinic.lower() not in title.lower():
        return f"{clinic}: {title}"
    return title or clinic or f"abre el filtro {fallback_filter} en el panel"


def review_display_title(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    title = str(item.get("title") or "").strip()
    if normalized_review_type(item) == "clinic_quality_audit":
        return re.sub(r"^Completar ficha:", "Revisión manual:", title, flags=re.I)
    return title


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


def review_clinic_key(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return str(item.get("clinic_slug") or item.get("clinic_name") or "").strip().lower()


def target_clinic_key(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return str(item.get("slug") or item.get("clinic_slug") or item.get("clinic_name") or "").strip().lower()


def aggregate_profile_queue_status(digest: dict[str, Any]) -> str:
    completeness = digest.get("profile_completeness") or {}
    visible = as_int(completeness.get("visible_clinics"))
    pending = as_int(completeness.get("with_pending_fields"))
    if visible and pending:
        return f"{pending}/{visible} fichas con campos pendientes; se revisan después de la prioridad actual"
    return "sin ficha pendiente medida"


def review_backlog_status(digest: dict[str, Any]) -> str:
    quality = digest.get("review_backlog_quality") or {}
    duplicate_clinics = as_int(quality.get("duplicate_enrichment_clinics"))
    duplicate_reviews = as_int(quality.get("duplicate_enrichment_reviews"))
    if not duplicate_clinics:
        return "sin duplicados de mejoras detectados"
    clinic_label = "clínica" if duplicate_clinics == 1 else "clínicas"
    return f"{duplicate_clinics} {clinic_label} con varias mejoras abiertas; {duplicate_reviews} tarjetas"


def profile_queue_signal(digest: dict[str, Any]) -> str:
    next_action = next_action_label(digest)
    if next_action in {"Mejorar fichas existentes", "Revisión manual de fichas"}:
        action_review = first_action_review(digest)
        target = digest.get("profile_next_target") if isinstance(digest.get("profile_next_target"), dict) else {}
        action_key = review_clinic_key(action_review)
        target_key = target_clinic_key(target)
        if action_key and target_key and action_key != target_key:
            return aggregate_profile_queue_status(digest)
        return next_profile_action(digest)
    return aggregate_profile_queue_status(digest)


def backlog_bottleneck_signal(digest: dict[str, Any]) -> str:
    quality = digest.get("review_backlog_quality") or {}
    duplicate_clinics = as_int(quality.get("duplicate_enrichment_clinics"))
    if not duplicate_clinics:
        return first_backlog_bottleneck(digest)
    guard = review_backlog_guard_status(digest)
    if guard.startswith("cerca del freno") or guard.startswith("freno activo"):
        return first_backlog_bottleneck(digest)
    clinic_label = "clínica" if duplicate_clinics == 1 else "clínicas"
    return f"{duplicate_clinics} {clinic_label} con mejoras repetidas; se ordenan después de la prioridad actual"


def review_professionals_note(item: dict[str, Any] | None) -> str:
    count = as_int((item or {}).get("professionals_count"))
    if not count:
        return ""
    word = "especialista recogido" if count == 1 else "especialistas recogidos"
    return f" Trae {count} {word}."


def review_case_line(item: dict[str, Any] | None, fallback_filter: str) -> str:
    return f"Caso visible: {review_name(item, fallback_filter)}." + review_professionals_note(item)


def review_first_step_copy(item: dict[str, Any]) -> list[str]:
    review_type = normalized_review_type(item)
    if review_type == "blocking_claim_review":
        return [
            "Primero revisa claims bloqueantes.",
            review_case_line(item, "Claims bloqueantes"),
        ]
    if review_type == "clinic_claim_request":
        return [
            "Primero revisa reclamaciones de ficha.",
            review_case_line(item, "Reclamaciones")
            + " No confirma identidad, no da acceso y no cambia datos por sí sola.",
        ]
    if review_type == "candidate_clinic":
        return [
            "Primero valida clínicas nuevas.",
            review_case_line(item, "Clínicas nuevas"),
        ]
    if review_type == "source_change_detected":
        return [
            "Primero revisa cambios de fuente.",
            review_case_line(item, "Cambios de fuente"),
        ]
    if review_type == "clinic_profile_enrichment":
        return [
            "Primero revisa mejoras de fichas existentes.",
            review_case_line(item, "Mejoras de ficha"),
        ]
    if review_type == "clinic_quality_audit":
        return [
            "Primero abre revisión manual de fichas incompletas.",
            review_case_line(item, "Auditorías"),
        ]
    return [
        "Primero abre la revisión prioritaria.",
        review_case_line(item, "Prioridad"),
    ]


def priority_review_click(digest: dict[str, Any]) -> str:
    counts = review_counts(digest)
    if counts.get("blocking_claim_review"):
        item = first_review(digest, "blocking_claim_review")
        if not item:
            return "Pulsa Abrir prioridad y abre el filtro Claims bloqueantes."
        return f"Pulsa Abrir prioridad: {review_name(item, 'Claims bloqueantes')}."
    if counts.get("clinic_claim_request"):
        return claim_request_click(digest)
    item = first_action_review(digest)
    if not item:
        return ""
    review_type = normalized_review_type(item)
    if review_type == "clinic_claim_request":
        return claim_request_click(digest)
    label = review_name(item, "Prioridad")
    note = review_professionals_note(item)
    if review_type == "clinic_quality_audit":
        return f"Pulsa Abrir prioridad: {label}; corrige solo ese campo con Revisión manual."
    return f"Pulsa Abrir prioridad: {label}.{note}"


def clinic_workgroup_click(digest: dict[str, Any]) -> str:
    group = digest.get("review_first_clinic_workgroup") or {}
    name = str(group.get("clinic_name") or group.get("clinic_slug") or "").strip()
    count = as_int(group.get("open_count"))
    if not name or not count:
        return ""
    return f"Pulsa Filtrar grupo y abre {name}: {count} tarjetas, una por una."


def claim_request_click(digest: dict[str, Any]) -> str:
    count = review_counts(digest).get("clinic_claim_request", 0)
    first = first_review(digest, "clinic_claim_request")
    if not count:
        return ""
    return (
        "Abre Reclamaciones y revisa "
        f"{review_name(first, 'Reclamaciones')}. "
        "No confirma identidad, no da acceso y no cambia datos por sí sola."
    )


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
        priority_review_click(digest),
        specialists_click(digest),
        google_maps_click(digest),
        clinic_workgroup_click(digest),
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
    if failed:
        return [
            "Primero revisa fallos técnicos.",
            "Hay trabajos fallidos; conviene corregirlos antes de aceptar nuevas fichas.",
        ]
    if counts.get("blocking_claim_review"):
        return [
            "Primero revisa claims bloqueantes.",
            review_case_line(first_review(digest, "blocking_claim_review"), "Claims bloqueantes"),
        ]
    if counts.get("clinic_claim_request"):
        return [
            "Primero revisa reclamaciones de ficha.",
            review_case_line(first_review(digest, "clinic_claim_request"), "Reclamaciones")
            + " No confirma identidad, no da acceso y no cambia datos por sí sola.",
        ]
    action_review = first_action_review(digest)
    if action_review:
        return review_first_step_copy(action_review)
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
            "Primero abre revisión manual de fichas incompletas.",
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
            "clinic_claim_request",
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
        f"- Publicación web: {publication_control_status(digest)}.",
        f"- Preparación para publicación: {publication_readiness_status(digest)}.",
        f"- Principal faltante para publicar: {top_publication_missing_field(digest)}.",
        f"- Siguiente publicación: {next_publication_action(digest)}.",
        f"- Madurez de auto-publicación: {maturity_status(digest)}.",
        "- Crear borrador no publica. Publicar se decide después en el editor, en Validación final.",
        "",
        "## Señales técnicas",
        f"- Clínicas visibles: {as_int(clinics.get('published'))} publicadas y {as_int(clinics.get('preliminary'))} preliminares.",
        f"- Completitud de fichas: {profile_completeness_status(digest)}.",
        f"- Campo más pendiente: {top_pending_profile_field(digest)}.",
        f"- Google Maps pendientes: {google_link_review_status(digest)}.",
        f"- Fichas pendientes: {profile_queue_signal(digest)}.",
        f"- Especialistas publicados: {specialist_status(digest)}.",
        f"- Tarjetas con especialistas: {specialist_review_status(digest)}.",
        f"- Siguiente especialistas: {next_specialist_action(digest)}.",
        f"- Fuentes: {source_status(digest)}.",
        f"- Cobertura fuentes: {source_coverage_status(digest)}.",
        f"- Siguiente fuente: {next_source_action(digest)}.",
        f"- Bandeja: {review_backlog_status(digest)}.",
        f"- Grupo por clínica: {first_clinic_workgroup(digest)}.",
        f"- Atascos de mejoras: {backlog_bottleneck_signal(digest)}.",
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
    parser.add_argument("--json", action="store_true", help="Print safe digest JSON instead of the Daniel brief.")
    parser.add_argument("--include-account-fields", action="store_true", help="Keep operator/account fields in JSON output for local debugging.")
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
        digest = safe_json_digest(digest, include_account_fields=args.include_account_fields)
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
