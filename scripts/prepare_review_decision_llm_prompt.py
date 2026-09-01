#!/usr/bin/env python3
"""Prepare a safe one-decision prompt for future LLM review assistance."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from review_proposal_decision_packets import DECISION_ACTIONS, PACKET_SCHEMA_VERSION, packet_is_llm_ready, redacted_text
from validate_review_decision_suggestion import select_packet


PROMPT_SCHEMA_VERSION = "review_decision_llm_prompt.v1"
VALIDATOR_SCRIPT = "scripts/validate_review_decision_suggestion.py"


def sanitize_for_prompt(value: Any, allow_full_values: bool = False) -> Any:
    if isinstance(value, list):
        return [sanitize_for_prompt(item, allow_full_values=allow_full_values) for item in value]
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if not allow_full_values and str(key) == "value":
                continue
            clean[str(key)] = sanitize_for_prompt(item, allow_full_values=allow_full_values)
        return clean
    if isinstance(value, str):
        return redacted_text(value, include_values=allow_full_values)
    return value


def packet_digest(packet: dict[str, Any]) -> dict[str, Any]:
    clinic = packet.get("clinic") if isinstance(packet.get("clinic"), dict) else {}
    fields = [
        {
            "key": item.get("key"),
            "label": item.get("label"),
            "google_maps_review": sanitize_for_prompt(item.get("google_maps_review") or {}),
            "google_reviews_review": sanitize_for_prompt(item.get("google_reviews_review") or {}),
        }
        for item in packet.get("proposed_change") or []
        if isinstance(item, dict)
    ]
    evidence_hosts = [
        item.get("host")
        for item in packet.get("evidence") or []
        if isinstance(item, dict) and item.get("host")
    ]
    manual_targets = [
        {"key": item.get("key"), "label": item.get("label")}
        for item in packet.get("manual_review_targets") or []
        if isinstance(item, dict) and item.get("key")
    ]
    manual_context = packet.get("manual_review_context") if isinstance(packet.get("manual_review_context"), dict) else {}
    manual_profile_context = (
        packet.get("manual_profile_edit_context")
        if isinstance(packet.get("manual_profile_edit_context"), dict)
        else {}
    )
    manual_profile_fields = [
        {
            "key": item.get("key"),
            "label": item.get("label"),
            "review_input_id": item.get("review_input_id"),
            "main_editor_target_id": item.get("main_editor_target_id"),
            "current": sanitize_for_prompt(item.get("current") or {}),
        }
        for item in manual_profile_context.get("fields") or []
        if isinstance(item, dict) and item.get("key")
    ]
    source_job = packet.get("source_job_request") if isinstance(packet.get("source_job_request"), dict) else {}
    source_context = packet.get("source_job_context") if isinstance(packet.get("source_job_context"), dict) else {}
    source_origin = packet.get("source_origin_status") if isinstance(packet.get("source_origin_status"), dict) else {}
    return {
        "review_id": packet.get("review_id"),
        "packet_schema_version": packet.get("schema_version") or PACKET_SCHEMA_VERSION,
        "clinic_name": clinic.get("name"),
        "display_title": packet.get("display_title") or packet.get("title"),
        "proposal_type": packet.get("proposal_type"),
        "review_type": packet.get("review_type"),
        "field_count": len(fields),
        "fields": fields,
        "evidence_hosts": evidence_hosts,
        "manual_review_targets": manual_targets,
        "manual_review_context": {
            "mode": manual_context.get("mode"),
            "operator_action": manual_context.get("operator_action"),
            "after_save": manual_context.get("after_save"),
            "source_handoff": sanitize_for_prompt(manual_context.get("source_handoff") or {}),
            "llm_boundary": manual_context.get("llm_boundary"),
        } if manual_context else {},
        "manual_profile_edit_context": {
            "available": bool(manual_profile_context.get("available")),
            "ui_label": manual_profile_context.get("ui_label"),
            "mode": manual_profile_context.get("mode"),
            "human_only": bool(manual_profile_context.get("human_only")),
            "write_policy": manual_profile_context.get("write_policy"),
            "allowed_actions_to_persist": manual_profile_context.get("allowed_actions_to_persist") or [],
            "reject_discards": bool(manual_profile_context.get("reject_discards")),
            "safe_to_auto_publish": bool(manual_profile_context.get("safe_to_auto_publish")),
            "field_count": manual_profile_context.get("field_count"),
            "fields": manual_profile_fields,
            "llm_boundary": manual_profile_context.get("llm_boundary"),
        } if manual_profile_context else {},
        "source_job_context": {
            "mode": source_context.get("mode"),
            "human_supplied_source": bool(source_context.get("human_supplied_source")),
            "source_host": source_context.get("source_host"),
            "ui_route": source_context.get("ui_route"),
            "target_scope": source_context.get("target_scope"),
            "requested_fields": source_context.get("requested_fields") or [],
            "requested_field_labels": source_context.get("requested_field_labels") or [],
            "primary_requested_fields": source_context.get("primary_requested_fields") or [],
            "primary_requested_field_labels": source_context.get("primary_requested_field_labels") or [],
            "operator_requested_field_keys": source_context.get("operator_requested_field_keys") or [],
            "operator_requested_field_labels": source_context.get("operator_requested_field_labels") or [],
            "operator_requested_field_summary": source_context.get("operator_requested_field_summary"),
            "allowed_output": source_context.get("allowed_output"),
            "write_policy": source_context.get("write_policy"),
            "llm_boundary": source_context.get("llm_boundary"),
        } if source_context else {},
        "source_origin_status": sanitize_for_prompt(source_origin) if source_origin else {},
        "source_job_request": {
            "status": source_job.get("status"),
            "source_requirement": source_job.get("source_requirement"),
            "ui_route": source_job.get("ui_route"),
            "target_scope": source_job.get("target_scope"),
            "requested_fields": source_job.get("requested_fields") or [],
            "primary_requested_fields": source_job.get("primary_requested_fields") or [],
        } if source_job else {},
        "warning_count": len(packet.get("warnings") or []),
    }


def expected_response_schema(packet: dict[str, Any]) -> dict[str, Any]:
    editable = [
        str(item.get("key"))
        for item in packet.get("editable_fields") or []
        if isinstance(item, dict) and item.get("key")
    ]
    manual_targets = [
        str(item.get("key"))
        for item in packet.get("manual_review_targets") or []
        if isinstance(item, dict) and item.get("key")
    ]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["review_id", "action", "reason"],
        "properties": {
            "review_id": {"type": "string", "const": str(packet.get("review_id") or "")},
            "action": {"type": "string", "enum": DECISION_ACTIONS},
            "reason": {"type": "string", "maxLength": 500},
            "warnings_to_show": {
                "type": "array",
                "items": {"type": "string", "maxLength": 300},
                "default": [],
            },
            "field_changes": {
                "type": "object",
                "propertyNames": {"enum": editable},
                "additionalProperties": True,
                "default": {},
            },
            "manual_review_target_key": {
                "type": "string",
                "enum": manual_targets,
            },
        },
    }


def system_prompt() -> str:
    return "\n".join([
        "Eres un asistente interno de Vitalarga para preparar una revisión humana.",
        "No publicas, no escribes en Supabase, no resuelves tarjetas y no das acceso a clínicas.",
        "Tu tarea es proponer una única acción para una única tarjeta: approve, reject o modify.",
        "Si propones modify, solo puedes incluir campos listados en editable_fields.",
        "Si no hay editable_fields pero hay manual_review_targets, puedes proponer modify con manual_review_target_key.",
        "manual_profile_edit_context describe campos que solo Daniel puede corregir en el panel; no los conviertas en field_changes.",
        "Responde solo JSON válido con el esquema indicado.",
    ])


def user_prompt(packet: dict[str, Any], allow_full_values: bool = False) -> str:
    safe_packet = sanitize_for_prompt(packet, allow_full_values=allow_full_values)
    parts = [
        "Revisa este paquete de una sola decisión.",
        "Mantén la respuesta breve y prudente.",
        "No introduzcas campos nuevos ni instrucciones operativas.",
        "Si hay warnings, conserva la revisión humana obligatoria.",
        "",
        "Paquete:",
        json.dumps(safe_packet, ensure_ascii=False, indent=2),
    ]
    return "\n".join(parts)


def build_prompt(packet: dict[str, Any], allow_full_values: bool = False) -> dict[str, Any]:
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "packet_digest": packet_digest(packet),
        "safe_default": not allow_full_values,
        "llm_role": "prepare_suggestions_only",
        "human_required": True,
        "write_policy": "no_writes",
        "validation_required": VALIDATOR_SCRIPT,
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(packet, allow_full_values=allow_full_values)},
        ],
        "expected_response_schema": expected_response_schema(packet),
    }


def require_llm_ready(packet: dict[str, Any]) -> None:
    if packet_is_llm_ready(packet):
        return
    raise SystemExit(
        "Packet is not LLM-ready: source-only proposal lacks operator/job context and no manual target route is available. "
        "Review manually or use review_llm_batch_preflight.py --compact before assisted batches."
    )


def load_json(path: Path | None) -> Any:
    if path is None or str(path) == "-":
        return json.loads(sys.stdin.read())
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-file", type=Path, required=True, help="Decision packet JSON file or packet report.")
    parser.add_argument("--review-id", default="", help="Packet review_id to select when packet-file is a report.")
    parser.add_argument("--require-llm-ready", action="store_true", help="Exit if the selected packet is source-only without operator/job context.")
    parser.add_argument("--allow-full-values", action="store_true", help="Keep raw packet values for deliberate local LLM preparation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = select_packet(load_json(args.packet_file), review_id=args.review_id)
    if args.require_llm_ready:
        require_llm_ready(packet)
    print(json.dumps(build_prompt(packet, allow_full_values=args.allow_full_values), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
