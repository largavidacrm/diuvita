#!/usr/bin/env python3
"""Read-only pre-SEO closure report for Vitalarga."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from admin_digest import as_int, load_digest, parse_timestamp
from review_backlog_brief import (
    backlog_guard,
    first_backlog_action,
    format_clinic_workgroup,
    load_backlog,
)
from submit_discovery_candidates import get_default_admin_email, load_env_file


DEFAULT_REVIEW_TARGET = 25


def clipped_items(items: list[Any], limit: int) -> list[Any]:
    return items[: max(1, min(20, int(limit)))]


def review_open_count(backlog: dict[str, Any], digest: dict[str, Any]) -> int:
    summary = backlog.get("summary") or {}
    if "open_reviews" in summary:
        return as_int(summary.get("open_reviews"))
    digest_summary = digest.get("summary") or {}
    reviews = digest_summary.get("reviews") or {}
    return as_int(reviews.get("open"))


def review_type_line(row: dict[str, Any]) -> str:
    label = row.get("review_type") or "revision"
    count = as_int(row.get("open_count"))
    priority = as_int(row.get("max_priority"))
    priority_text = f", max P{priority}" if priority else ""
    return f"- {label}: {count} abiertas{priority_text}"


def next_pre_seo_review_action(backlog: dict[str, Any]) -> str:
    workgroups = backlog.get("clinic_workgroups") or []
    if not workgroups:
        return first_backlog_action(backlog)
    row = workgroups[0]
    if not isinstance(row, dict):
        return first_backlog_action(backlog)
    name = row.get("clinic_name") or row.get("clinic_slug") or "clinica sin nombre"
    cards = as_int(row.get("card_count"))
    if as_int(row.get("blocking_claim_reviews")):
        detail = "claims bloqueantes"
    elif as_int(row.get("claim_request_reviews")):
        detail = "reclamacion de ficha"
    elif as_int(row.get("source_change_reviews")):
        detail = "cambios de fuente"
    elif as_int(row.get("enrichment_reviews")):
        detail = "mejoras de ficha"
    elif as_int(row.get("quality_reviews")):
        detail = "revision manual"
    elif as_int(row.get("candidate_reviews")):
        detail = "clinica candidata"
    else:
        detail = "prioridad normal"
    suffix = "tarjeta" if cards == 1 else "tarjetas"
    return f"Revisar {name}: {cards} {suffix}, empezando por {detail}"


def top_missing_fields(publication_readiness: dict[str, Any]) -> str:
    fields = publication_readiness.get("top_missing_fields") or []
    labels = []
    for item in fields[:5]:
        if not isinstance(item, dict):
            continue
        field = item.get("field") or "campo"
        labels.append(f"{field}: {as_int(item.get('count'))}")
    return ", ".join(labels) or "sin faltantes medidos"


def publication_readiness_line(digest: dict[str, Any]) -> str:
    readiness = digest.get("publication_readiness") or {}
    measured = as_int(readiness.get("clinics_measured"))
    ready = as_int(readiness.get("ready_clinics"))
    missing = as_int(readiness.get("clinics_with_missing_fields"))
    blocking = as_int(readiness.get("clinics_with_blocking_reviews"))
    if not measured:
        return "sin medicion de fichas publicables"
    return f"{ready}/{measured} sin faltantes obligatorios; {missing} con faltantes; {blocking} con claims bloqueantes"


def source_coverage_line(digest: dict[str, Any]) -> str:
    coverage = digest.get("source_coverage") or {}
    visible = as_int(coverage.get("visible_clinics"))
    with_sources = as_int(coverage.get("clinics_with_sources"))
    hydrated = as_int(coverage.get("clinics_with_hydrated_sources"))
    without_sources = as_int(coverage.get("clinics_without_sources"))
    needing = as_int(coverage.get("clinics_needing_source_work"))
    if not visible:
        return "sin medicion de fuentes visibles"
    return (
        f"{with_sources}/{visible} fichas con fuente; "
        f"{hydrated}/{visible} hidratadas; "
        f"{without_sources} sin fuente; {needing} con trabajo pendiente"
    )


def llm_review_readiness_line(digest: dict[str, Any]) -> str:
    audit = digest.get("review_source_origin_audit") or {}
    cards = as_int(audit.get("cards"))
    if not cards:
        return "sin propuestas medidas para ayuda IA"
    ready = as_int(audit.get("context_ready"))
    source_only = as_int(audit.get("source_without_context"))
    recoverable = as_int(audit.get("recoverable_from_job"))
    no_source = as_int(audit.get("no_source_context"))
    preparable = ready + source_only
    return (
        f"{preparable}/{cards} preparables para ayuda IA; "
        f"{ready} con contexto completo; "
        f"{recoverable} recuperables desde trabajo; "
        f"{source_only} acotadas a campos propuestos; "
        f"{no_source} sin fuente"
    )


def automation_is_safe(digest: dict[str, Any]) -> bool:
    summary = digest.get("summary") or {}
    automation = summary.get("automation") or {}
    return not bool(automation.get("auto_publish_enabled"))


def gate(label: str, ok: bool, detail: str, blocks_programmatic: bool = True) -> dict[str, Any]:
    return {
        "label": label,
        "ok": bool(ok),
        "detail": detail,
        "blocks_programmatic": bool(blocks_programmatic),
    }


def build_gates(digest: dict[str, Any], backlog: dict[str, Any], review_target: int) -> list[dict[str, Any]]:
    open_reviews = review_open_count(backlog, digest)
    backlog_summary = backlog.get("summary") or {}
    duplicates = as_int(backlog_summary.get("duplicate_enrichment_reviews"))
    publication = digest.get("publication_readiness") or {}
    measured = as_int(publication.get("clinics_measured"))
    missing = as_int(publication.get("clinics_with_missing_fields"))
    blocking = as_int(publication.get("clinics_with_blocking_reviews"))
    coverage = digest.get("source_coverage") or {}
    source_visible = as_int(coverage.get("visible_clinics"))
    source_needing = as_int(coverage.get("clinics_needing_source_work"))
    origin = digest.get("review_source_origin_audit") or {}
    origin_problems = as_int(origin.get("recoverable_from_job")) + as_int(origin.get("no_source_context"))

    return [
        gate(
            "Bandeja <= 25",
            open_reviews <= review_target,
            f"{open_reviews} abiertas frente a objetivo {review_target}",
        ),
        gate(
            "Una cola sin duplicados obvios",
            duplicates == 0,
            f"{duplicates} tarjetas en grupos duplicados de mejora",
        ),
        gate(
            "Campos base publicables",
            measured > 0 and missing == 0 and blocking == 0,
            f"{publication_readiness_line(digest)}; faltantes principales: {top_missing_fields(publication)}",
        ),
        gate(
            "Trazabilidad suficiente",
            source_visible > 0 and source_needing == 0 and origin_problems == 0,
            f"{source_coverage_line(digest)}; ayuda IA: {llm_review_readiness_line(digest)}",
        ),
        gate(
            "Auto-publicacion apagada",
            automation_is_safe(digest),
            "los agentes no publican datos solos",
            blocks_programmatic=False,
        ),
    ]


def programmatic_seo_status(gates: list[dict[str, Any]]) -> str:
    blockers = [
        gate_item["label"]
        for gate_item in gates
        if gate_item.get("blocks_programmatic") and not gate_item.get("ok")
    ]
    if not blockers:
        return "preparado para plantear SEO programatico con aprobacion de Daniel"
    return "esperar: " + "; ".join(blockers)


def status_prefix(ok: bool) -> str:
    return "OK" if ok else "PENDIENTE"


def build_pre_seo_report(
    digest: dict[str, Any],
    backlog: dict[str, Any],
    review_target: int = DEFAULT_REVIEW_TARGET,
    limit: int = 8,
) -> dict[str, Any]:
    gates = build_gates(digest, backlog, review_target)
    backlog_summary = backlog.get("summary") or {}
    return {
        "generated_at": digest.get("generated_at") or backlog.get("generated_at"),
        "writes_data": False,
        "pushes_or_deploys": False,
        "review_target": int(review_target),
        "review_open_count": review_open_count(backlog, digest),
        "backlog_guard": backlog_guard(backlog_summary),
        "next_review_action": next_pre_seo_review_action(backlog),
        "review_type_summary": clipped_items(backlog.get("review_type_summary") or [], limit),
        "clinic_workgroups": clipped_items(backlog.get("clinic_workgroups") or [], limit),
        "duplicate_enrichment_count": as_int(backlog_summary.get("duplicate_enrichment_reviews")),
        "publication_readiness": digest.get("publication_readiness") or {},
        "source_coverage": digest.get("source_coverage") or {},
        "review_source_origin_audit": digest.get("review_source_origin_audit") or {},
        "gates": gates,
        "technical_seo_status": "puede seguir en local",
        "programmatic_seo_status": programmatic_seo_status(gates),
    }


def format_gate(gate_item: dict[str, Any]) -> str:
    return f"- {status_prefix(gate_item.get('ok'))} · {gate_item.get('label')}: {gate_item.get('detail')}"


def format_pre_seo_report(report: dict[str, Any]) -> str:
    open_reviews = as_int(report.get("review_open_count"))
    target = as_int(report.get("review_target")) or DEFAULT_REVIEW_TARGET
    target_label = "cumplido" if open_reviews <= target else "pendiente"
    review_types = report.get("review_type_summary") or []
    workgroups = report.get("clinic_workgroups") or []
    gates = report.get("gates") or []

    lines = [
        "# Vitalarga: cierre pre-SEO",
        "",
        f"Generado: {parse_timestamp(report.get('generated_at'))}",
        "- Writes data: no",
        "- Push/deploy: no",
        "",
        "## Lectura rapida",
        f"- Bandeja: {open_reviews} abiertas; objetivo <={target} {target_label}.",
        f"- SEO tecnico: {report.get('technical_seo_status')}.",
        f"- SEO programatico: {report.get('programmatic_seo_status')}.",
        f"- Siguiente revision humana: {report.get('next_review_action') or 'sin revision prioritaria medida'}.",
        "",
        "## Gates",
        *[format_gate(item) for item in gates],
        "",
        "## Bandeja",
        f"- Estado seguro de escritura: {report.get('backlog_guard')}.",
        f"- Grupos duplicados de mejora: {as_int(report.get('duplicate_enrichment_count'))} tarjetas.",
    ]
    if review_types:
        lines.append("- Tipos abiertos:")
        lines.extend(review_type_line(row) for row in review_types if isinstance(row, dict))
    else:
        lines.append("- Tipos abiertos: sin datos.")

    lines.extend([
        "",
        "## Publicacion y campos base",
        f"- Preparacion para publicar: {publication_readiness_line({'publication_readiness': report.get('publication_readiness') or {}})}.",
        f"- Faltantes principales: {top_missing_fields(report.get('publication_readiness') or {})}.",
        "",
        "## Trazabilidad y ayuda IA",
        f"- Fuentes: {source_coverage_line({'source_coverage': report.get('source_coverage') or {}})}.",
        f"- Propuestas para LLM: {llm_review_readiness_line({'review_source_origin_audit': report.get('review_source_origin_audit') or {}})}.",
        "",
        "## Proximos focos humanos",
    ])
    if workgroups:
        lines.extend(format_clinic_workgroup(row) for row in workgroups if isinstance(row, dict))
    else:
        lines.append("- No hay grupos de revision por clinica medidos.")
    lines.extend([
        "",
        "Nota: este informe no publica, no edita clinicas, no resuelve tarjetas y no cambia Netlify.",
    ])
    return "\n".join(lines) + "\n"


def load_pre_seo_report(admin_email: str, limit: int, review_target: int, local_env: dict[str, str]) -> dict[str, Any]:
    digest = load_digest(admin_email, limit, local_env)
    backlog = load_backlog(limit, local_env)
    return build_pre_seo_report(digest, backlog, review_target, limit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", help="Admin email used to read the protected dashboard summary.")
    parser.add_argument("--limit", type=int, default=8, help="Maximum review groups to include.")
    parser.add_argument("--review-target", type=int, default=DEFAULT_REVIEW_TARGET)
    parser.add_argument("--json", action="store_true", help="Print structured JSON instead of the readable report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.review_target < 1:
        raise SystemExit("--review-target must be at least 1.")
    local_env = load_env_file()
    admin_email = args.admin_email or get_default_admin_email(local_env)
    report = load_pre_seo_report(admin_email, args.limit, args.review_target, local_env)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_pre_seo_report(report), end="")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
