#!/usr/bin/env python3
"""Preflight open review packets before any future LLM-assisted batch."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from prepare_review_decision_llm_prompt import build_prompt, require_llm_ready
from review_proposal_decision_packets import (
    build_report,
    load_env_file,
    load_input_file,
    load_rows,
    packet_is_llm_ready,
    packet_llm_readiness_status,
)


PREFLIGHT_SCHEMA_VERSION = "review_llm_batch_preflight.v1"


def source_origin_label(packet: dict[str, Any]) -> str:
    status = packet.get("source_origin_status")
    if isinstance(status, dict):
        return str(status.get("status") or "no_source_origin_status")
    return "no_source_origin_status"


def manual_target_keys(packet: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for item in packet.get("manual_review_targets") or []:
        if isinstance(item, dict) and item.get("key"):
            keys.append(str(item["key"]))
    return keys


def manual_profile_edit_available(packet: dict[str, Any]) -> bool:
    context = packet.get("manual_profile_edit_context")
    return bool(isinstance(context, dict) and context.get("available"))


def blocked_reason(packet: dict[str, Any]) -> str:
    status = source_origin_label(packet)
    if status == "source_without_context":
        return "source_without_context: revisar manualmente o crear trabajo desde una URL oficial aportada por Daniel."
    return "packet_failed_strict_llm_ready_check"


def preflight_item(packet: dict[str, Any]) -> dict[str, Any]:
    clinic = packet.get("clinic") if isinstance(packet.get("clinic"), dict) else {}
    readiness_status = packet_llm_readiness_status(packet)
    item = {
        "review_id": packet.get("review_id"),
        "title": packet.get("display_title") or packet.get("title"),
        "clinic_name": clinic.get("name"),
        "review_type": packet.get("review_type"),
        "proposal_type": packet.get("proposal_type"),
        "source_origin_status": source_origin_label(packet),
        "llm_readiness_status": readiness_status,
        "manual_review_targets": manual_target_keys(packet),
        "manual_profile_edit_available": manual_profile_edit_available(packet),
        "field_count": len(packet.get("proposed_change") or []),
        "warning_count": len(packet.get("warnings") or []),
        "human_required": True,
        "calls_llm": False,
        "writes_data": False,
    }
    if not packet_is_llm_ready(packet):
        item.update({
            "strict_prompt_status": "blocked",
            "llm_ready": False,
            "blocked_reason": blocked_reason(packet),
            "next_step": "human_review_or_source_handoff",
        })
        return item
    try:
        require_llm_ready(packet)
        prompt = build_prompt(packet)
    except SystemExit:
        item.update({
            "strict_prompt_status": "blocked",
            "llm_ready": False,
            "blocked_reason": blocked_reason(packet),
            "next_step": "human_review_or_source_handoff",
        })
        return item
    item.update({
        "strict_prompt_status": "ready",
        "llm_ready": True,
        "prompt_schema_version": prompt.get("schema_version"),
        "prompt_write_policy": prompt.get("write_policy"),
        "expected_actions": prompt.get("expected_response_schema", {})
        .get("properties", {})
        .get("action", {})
        .get("enum", []),
        "next_step": "safe_to_prepare_manual_navigation_suggestion_then_validate_locally"
        if readiness_status == "manual_target_prompt_ready"
        else "safe_to_prepare_llm_suggestion_then_validate_locally",
    })
    return item


def summarize_items(items: list[dict[str, Any]], total_packets: int) -> dict[str, Any]:
    ready = [item for item in items if item.get("llm_ready")]
    blocked = [item for item in items if not item.get("llm_ready")]
    source_only = [
        item for item in items
        if item.get("source_origin_status") == "source_without_context"
    ]
    blocked_source_only = [
        item for item in blocked
        if item.get("source_origin_status") == "source_without_context"
    ]
    manual_target_ready = [
        item for item in ready
        if item.get("llm_readiness_status") == "manual_target_prompt_ready"
    ]
    manual_targets = [
        item for item in items
        if item.get("manual_review_targets")
    ]
    manual_profile_edits = [
        item for item in items
        if item.get("manual_profile_edit_available")
    ]
    return {
        "total_packets": total_packets,
        "reported_packets": len(items),
        "llm_ready": len(ready),
        "blocked": len(blocked),
        "source_without_context": len(source_only),
        "blocked_source_without_context": len(blocked_source_only),
        "manual_target_prompt_ready": len(manual_target_ready),
        "manual_review_target_packets": len(manual_targets),
        "manual_profile_edit_available": len(manual_profile_edits),
    }


def compact_item_line(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "Revisión sin título")
    if item.get("llm_readiness_status") == "manual_target_prompt_ready":
        status = "ruta manual lista"
    elif item.get("llm_ready"):
        status = "lista para LLM"
    else:
        status = "manual"
    target_keys = item.get("manual_review_targets") or []
    target_text = f" · campos: {', '.join(target_keys[:4])}" if target_keys else ""
    if len(target_keys) > 4:
        target_text += f" +{len(target_keys) - 4}"
    profile_text = " · edición ficha" if item.get("manual_profile_edit_available") else ""
    reason = ""
    if not item.get("llm_ready") and item.get("blocked_reason"):
        reason = " · " + str(item["blocked_reason"]).split(":", 1)[0]
    return f"- {title}: {status}{target_text}{profile_text}{reason}"


def format_preflight_report(report: dict[str, Any], limit: int = 8) -> str:
    summary = report.get("summary") or {}
    items = [item for item in report.get("items") or [] if isinstance(item, dict)]
    blocked = [item for item in items if not item.get("llm_ready")]
    ready = [item for item in items if item.get("llm_ready")]
    lines = [
        "# Preflight LLM de revisiones",
        "",
        "Lectura: este informe no llama a ningún LLM, no escribe datos y no resuelve tarjetas.",
        "",
        "## Resumen",
        f"- Preparables para LLM estricto: {summary.get('llm_ready', 0)}/{summary.get('total_packets', 0)}",
        f"- Rutas manuales listas: {summary.get('manual_target_prompt_ready', 0)}",
        f"- Bloqueadas: {summary.get('blocked', 0)}",
        f"- Bloqueadas por fuente sin contexto: {summary.get('blocked_source_without_context', 0)}",
        f"- Con campo manual detectado: {summary.get('manual_review_target_packets', 0)}",
        f"- Con edición manual de ficha: {summary.get('manual_profile_edit_available', 0)}",
    ]
    if ready:
        lines.extend([
            "",
            "## Listas para preparar sugerencia",
            *[compact_item_line(item) for item in ready[:limit]],
        ])
    if blocked:
        lines.extend([
            "",
            "## Mantener manuales o pasar URL oficial",
            *[compact_item_line(item) for item in blocked[:limit]],
        ])
    shown_count = min(len(ready), limit) + min(len(blocked), limit)
    if len(items) > shown_count:
        lines.append(f"- ... {len(items) - shown_count} tarjetas más en esta lectura.")
    return "\n".join(lines)


def preflight_report(
    rows: list[dict[str, Any]],
    llm_ready_only: bool = False,
) -> dict[str, Any]:
    packet_report = build_report(rows, include_values=False, llm_ready_only=False)
    packets = packet_report["packets"]
    items = [preflight_item(packet) for packet in packets]
    if llm_ready_only:
        items = [item for item in items if item.get("llm_ready")]
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "writes_data": False,
        "calls_llm": False,
        "human_required": True,
        "llm_ready_only": llm_ready_only,
        "decision_scope": "one_card_one_decision",
        "summary": summarize_items(items, total_packets=len(packets)),
        "items": items,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--clinic", default="", help="Clinic name, slug or review-title fragment.")
    parser.add_argument("--review-id", default="", help="Open review_queue id.")
    parser.add_argument("--input-file", type=Path, help="Read review rows from a local JSON file instead of Supabase.")
    parser.add_argument("--llm-ready-only", action="store_true", help="Report only packets that pass strict LLM preflight.")
    parser.add_argument("--fail-if-blocked", action="store_true", help="Exit non-zero when any reported packet is blocked.")
    parser.add_argument("--compact", action="store_true", help="Print a short Spanish summary instead of JSON.")
    parser.add_argument("--compact-limit", type=int, default=8, help="Maximum item lines shown in compact mode.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.input_file:
        rows = load_input_file(args.input_file)
    else:
        rows = load_rows(args.limit, load_env_file(), clinic=args.clinic, review_id=args.review_id)
    report = preflight_report(rows, llm_ready_only=args.llm_ready_only)
    if args.compact:
        print(format_preflight_report(report, limit=max(1, args.compact_limit)))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.fail_if_blocked and report["summary"]["blocked"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
