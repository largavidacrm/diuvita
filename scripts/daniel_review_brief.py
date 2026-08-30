#!/usr/bin/env python3
"""Print a plain-Spanish, read-only review brief for Daniel."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import as_int, load_digest, next_action_label, parse_timestamp
from submit_discovery_candidates import get_default_admin_email, load_env_file


TYPE_LABELS = {
    "blocking_claim_review": "claims bloqueantes",
    "candidate_clinic": "clínicas nuevas",
    "clinic_profile_enrichment": "mejoras de ficha",
    "source_change_detected": "cambios de fuente",
    "clinic_quality_audit": "auditorías de calidad",
}


def review_counts(digest: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in digest.get("reviews_by_type") or []:
        review_type = str(item.get("review_type") or "")
        if review_type:
            counts[review_type] = as_int(item.get("open_count"))
    return counts


def review_label(review_type: str) -> str:
    return TYPE_LABELS.get(review_type, review_type.replace("_", " "))


def plural(value: int, singular: str, plural_text: str) -> str:
    return singular if value == 1 else plural_text


def first_review(digest: dict[str, Any], review_type: str) -> dict[str, Any] | None:
    for item in digest.get("open_reviews") or []:
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
            f"Caso visible: {review_name(first_review(digest, 'blocking_claim_review'), 'Claims bloqueantes')}.",
        ]
    if counts.get("candidate_clinic"):
        return [
            "Primero valida clínicas nuevas.",
            f"Caso visible: {review_name(first_review(digest, 'candidate_clinic'), 'Clínicas nuevas')}.",
        ]
    if counts.get("source_change_detected"):
        return [
            "Primero revisa cambios de fuente.",
            f"Caso visible: {review_name(first_review(digest, 'source_change_detected'), 'Cambios de fuente')}.",
        ]
    if counts.get("clinic_profile_enrichment"):
        return [
            "Primero revisa mejoras de fichas existentes.",
            f"Caso visible: {review_name(first_review(digest, 'clinic_profile_enrichment'), 'Mejoras de ficha')}.",
        ]
    if counts.get("clinic_quality_audit"):
        return [
            "Primero completa fichas incompletas.",
            f"Caso visible: {review_name(first_review(digest, 'clinic_quality_audit'), 'Auditorías')}.",
        ]
    return ["No hay una acción urgente.", "Puedes revisar el panel o dejar que el sistema siga en modo sombra."]


def format_brief(digest: dict[str, Any]) -> str:
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
        "# Diuvita: brief de revisión",
        "",
        f"Generado: {parse_timestamp(digest.get('generated_at') or summary.get('generated_at'))}",
        "",
        "## Qué mirar primero",
        f"- {first_lines[0]}",
        f"- {first_lines[1]}",
        f"- Acción sugerida por el sistema: {next_action}.",
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
                    f"- {count} {review_label(review_type)} {plural(count, 'pendiente', 'pendientes')}."
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
        f"- Fuentes: {source_status(digest)}.",
        f"- Fallos técnicos abiertos: {failed_jobs}.",
        "",
        "Panel: https://www.diuvita.com/admin/",
    ])

    return "\n".join(output) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used to read the protected dashboard summary.")
    parser.add_argument("--limit", type=int, default=30, help="Maximum open reviews and failed jobs to inspect.")
    parser.add_argument("--json", action="store_true", help="Print raw digest JSON instead of the Daniel brief.")
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
        print(format_brief(digest), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
