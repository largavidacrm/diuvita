#!/usr/bin/env python3
"""Summarize safe operator routes for open Vitalarga review cards."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from review_proposal_decision_packets import (
    build_report,
    load_env_file,
    load_input_file,
    load_rows,
    packet_llm_readiness_status,
)


ROUTE_BRIEF_SCHEMA_VERSION = "manual_review_route_brief.v1"


def _clean_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _clean_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _source_origin_status(packet: dict[str, Any]) -> str:
    status = _clean_dict(packet.get("source_origin_status"))
    return str(status.get("status") or "none")


def _primary_manual_target(packet: dict[str, Any]) -> dict[str, Any]:
    context = _clean_dict(packet.get("manual_review_context"))
    target = _clean_dict(context.get("primary_target"))
    if target:
        return target
    targets = _clean_list(packet.get("manual_review_targets"))
    return targets[0] if targets else {}


def _manual_target_labels(packet: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for target in _clean_list(packet.get("manual_review_targets")):
        label = str(target.get("label") or target.get("key") or "").strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def _source_request_summary(packet: dict[str, Any]) -> dict[str, Any]:
    request = _clean_dict(packet.get("source_job_request"))
    if not request:
        return {}
    fields = request.get("primary_requested_field_labels") or request.get("requested_field_labels") or []
    field_labels = [str(item).strip() for item in fields if str(item or "").strip()]
    return {
        "available": True,
        "source_requirement": request.get("source_requirement"),
        "target_scope": request.get("target_scope"),
        "ui_route": request.get("ui_route"),
        "allowed_output": request.get("allowed_output"),
        "primary_field_labels": field_labels[:3],
    }


def route_item(packet: dict[str, Any]) -> dict[str, Any]:
    clinic = _clean_dict(packet.get("clinic"))
    primary_target = _primary_manual_target(packet)
    source_request = _source_request_summary(packet)
    readiness = packet_llm_readiness_status(packet)
    source_origin = _source_origin_status(packet)
    editable_fields = _clean_list(packet.get("editable_fields"))
    target_labels = _manual_target_labels(packet)

    if primary_target:
        operator_action = "open_manual_field"
        human_next_step = f"Desde la propuesta, abrir la ficha y editar {primary_target.get('label') or primary_target.get('key')}."
    elif source_request and source_request.get("source_requirement"):
        operator_action = "request_official_source"
        human_next_step = "Pedir o pegar una URL oficial para que el agente prepare una propuesta revisable."
    elif source_origin == "source_without_context" and editable_fields:
        operator_action = "review_proposed_change_source_only"
        human_next_step = "Validar o modificar solo el cambio propuesto; la ayuda LLM queda limitada a esos campos."
    elif source_origin == "source_without_context":
        operator_action = "manual_review_source_without_context"
        human_next_step = "Revisar manualmente; no hay propuesta editable ni contexto suficiente para LLM."
    elif editable_fields:
        operator_action = "review_proposed_change"
        human_next_step = "Validar solo el cambio propuesto en esta tarjeta."
    else:
        operator_action = "manual_review_required"
        human_next_step = "Abrir la tarjeta y decidir sin automatizar."

    return {
        "review_id": packet.get("review_id"),
        "title": packet.get("display_title") or packet.get("title"),
        "clinic_name": clinic.get("name"),
        "review_type": packet.get("review_type"),
        "proposal_type": packet.get("proposal_type"),
        "priority": packet.get("priority"),
        "created_at": packet.get("created_at"),
        "operator_action": operator_action,
        "human_next_step": human_next_step,
        "llm_readiness_status": readiness,
        "llm_help_scope": "manual_navigation_only"
        if readiness == "manual_target_prompt_ready"
        else "legacy_source_explicit_fields_only"
        if readiness == "legacy_source_prompt_ready"
        else "blocked_without_operator_context"
        if readiness == "blocked_source_without_context"
        else "prepare_suggestion_then_validate_locally",
        "manual_primary_target": {
            "key": primary_target.get("key"),
            "label": primary_target.get("label"),
            "admin_target_id": primary_target.get("admin_target_id"),
        } if primary_target else {},
        "manual_target_labels": target_labels,
        "source_origin_status": source_origin,
        "source_handoff": source_request,
        "editable_field_count": len(editable_fields),
        "proposed_field_count": len(packet.get("proposed_change") or []),
        "warning_count": len(packet.get("warnings") or []),
        "writes_data": False,
        "calls_llm": False,
    }


def summarize_items(items: list[dict[str, Any]], total_packets: int) -> dict[str, Any]:
    return {
        "total_packets": total_packets,
        "reported_packets": len(items),
        "manual_field_routes": sum(1 for item in items if item["operator_action"] == "open_manual_field"),
        "source_handoff_available": sum(1 for item in items if item.get("source_handoff")),
        "source_without_context": sum(1 for item in items if item.get("source_origin_status") == "source_without_context"),
        "source_only_reviewable": sum(1 for item in items if item["operator_action"] == "review_proposed_change_source_only"),
        "legacy_source_llm_ready": sum(1 for item in items if item.get("llm_help_scope") == "legacy_source_explicit_fields_only"),
        "manual_navigation_llm_ready": sum(1 for item in items if item.get("llm_help_scope") == "manual_navigation_only"),
        "blocked_without_operator_context": sum(1 for item in items if item.get("llm_help_scope") == "blocked_without_operator_context"),
        "direct_change_reviews": sum(1 for item in items if item["operator_action"] in {"review_proposed_change", "review_proposed_change_source_only"}),
    }


def route_report(rows: list[dict[str, Any]], manual_first: bool = True) -> dict[str, Any]:
    packet_report = build_report(rows, include_values=False, llm_ready_only=False)
    packets = packet_report["packets"]
    items = [route_item(packet) for packet in packets]
    if manual_first:
        order = {
            "open_manual_field": 0,
            "request_official_source": 1,
            "review_proposed_change_source_only": 2,
            "manual_review_source_without_context": 3,
            "review_proposed_change": 4,
            "manual_review_required": 5,
        }
        items = sorted(items, key=lambda item: (order.get(item["operator_action"], 9), -int(item.get("priority") or 0)))
    return {
        "schema_version": ROUTE_BRIEF_SCHEMA_VERSION,
        "writes_data": False,
        "calls_llm": False,
        "human_required": True,
        "decision_scope": "one_card_one_decision",
        "summary": summarize_items(items, total_packets=len(packets)),
        "items": items,
    }


def compact_item_line(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "Revisión sin título")
    action = item.get("operator_action")
    if action == "open_manual_field":
        target = _clean_dict(item.get("manual_primary_target"))
        label = target.get("label") or "campo pendiente"
        return f"- {title}: desde la propuesta, abrir {label} en ficha."
    if action == "request_official_source":
        source = _clean_dict(item.get("source_handoff"))
        labels = source.get("primary_field_labels") or []
        label_text = ", ".join(labels) if labels else "el campo pendiente"
        return f"- {title}: pegar URL oficial para {label_text}; solo creará propuesta revisable."
    if action == "manual_review_source_without_context":
        return f"- {title}: revisar manualmente; sin propuesta editable ni contexto suficiente para LLM."
    if action == "review_proposed_change_source_only":
        return f"- {title}: revisar/modificar solo campos propuestos; fuente heredada acotada para ayuda LLM."
    if action == "review_proposed_change":
        return f"- {title}: decidir solo el cambio propuesto."
    return f"- {title}: revisión humana requerida."


def format_route_report(report: dict[str, Any], limit: int = 10) -> str:
    summary = report.get("summary") or {}
    items = [item for item in report.get("items") or [] if isinstance(item, dict)]
    lines = [
        "# Rutas de revisión manual",
        "",
        "Lectura: no llama a ningún LLM, no escribe datos y no resuelve tarjetas.",
        "",
        "## Resumen",
        f"- Tarjetas leídas: {summary.get('reported_packets', 0)}/{summary.get('total_packets', 0)}",
        f"- Abren campo directo: {summary.get('manual_field_routes', 0)}",
        f"- Permiten pasar URL oficial al agente: {summary.get('source_handoff_available', 0)}",
        f"- Listas para ayuda LLM de navegación: {summary.get('manual_navigation_llm_ready', 0)}",
        f"- Fuentes heredadas listas con límites: {summary.get('legacy_source_llm_ready', 0)}",
        f"- Revisiones con fuente heredada: {summary.get('source_only_reviewable', 0)}",
        f"- Bloqueadas para LLM por fuente sin contexto: {summary.get('blocked_without_operator_context', 0)}",
    ]
    if items:
        lines.extend([
            "",
            "## Siguiente lectura operativa",
            *[compact_item_line(item) for item in items[:limit]],
        ])
    if len(items) > limit:
        lines.append(f"- ... {len(items) - limit} tarjetas más.")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--clinic", default="", help="Clinic name, slug or review-title fragment.")
    parser.add_argument("--review-id", default="", help="Open review_queue id.")
    parser.add_argument("--input-file", type=Path, help="Read review rows from a local JSON file instead of Supabase.")
    parser.add_argument("--preserve-order", action="store_true", help="Keep queue order instead of grouping manual routes first.")
    parser.add_argument("--compact", action="store_true", help="Print a short Spanish summary instead of JSON.")
    parser.add_argument("--compact-limit", type=int, default=10, help="Maximum item lines shown in compact mode.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input_file:
        rows = load_input_file(args.input_file)
    else:
        rows = load_rows(args.limit, load_env_file(), clinic=args.clinic, review_id=args.review_id)
    report = route_report(rows, manual_first=not args.preserve_order)
    if args.compact:
        print(format_route_report(report, limit=max(1, args.compact_limit)))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
