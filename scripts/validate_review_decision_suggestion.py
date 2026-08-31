#!/usr/bin/env python3
"""Validate future LLM suggestions against one review decision packet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from review_proposal_decision_packets import (
    DECISION_ACTIONS,
    canonical_field,
    maps_warning,
    phone_warning,
    redacted_text,
)


GUARD_SCHEMA_VERSION = "review_decision_suggestion_guard.v1"
ACTION_ALIASES = {
    "approve": "approve",
    "aprove": "approve",
    "aprobar": "approve",
    "aceptar": "approve",
    "reject": "reject",
    "dismiss": "reject",
    "rechazar": "reject",
    "descartar": "reject",
    "modify": "modify",
    "modificar": "modify",
    "corregir": "modify",
}
FORBIDDEN_CONTROL_KEYS = {
    "admin_create_draft_clinic_from_review_v2",
    "admin_resolve_review_item",
    "admin_update_clinic",
    "auto_publish",
    "deploy",
    "netlify",
    "publish",
    "published",
    "push",
    "resolve",
    "resolved",
    "rpc",
    "sql",
    "status",
    "supabase",
    "write",
}
HIGH_ATTENTION_FIELDS = {
    "google_maps_url",
    "google_reviews_url",
    "locations",
    "maps_url",
    "phone_fixed",
    "phone_mobile",
    "phone_whatsapp",
    "pricing_url",
    "profesionales",
    "public_pricing",
    "team_credentialing_visible",
    "telefono",
}
HIGH_ATTENTION_REVIEW_TYPES = {
    "blocking_claim_review",
    "clinic_claim_request",
    "specialist_review",
}
SUGGESTION_CHANGE_KEYS = ("field_changes", "changes", "modified_fields", "proposed_fields")
SUGGESTION_MANUAL_TARGET_KEYS = ("manual_review_target_key", "manual_target_key", "target_field")
ALLOWED_SUGGESTION_KEYS = {
    "action",
    "field_changes",
    "changes",
    "manual_review_target_key",
    "manual_target_key",
    "modified_fields",
    "proposed_fields",
    "rationale",
    "reason",
    "review_id",
    "target_field",
    "warnings",
    "warnings_to_show",
}


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_value(item) for item in value)
    if isinstance(value, dict):
        return any(has_value(item) for item in value.values())
    return True


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def clean_text(value: Any, include_values: bool = False, max_length: int = 500) -> str:
    clean = redacted_text(value, include_values=include_values)
    if len(clean) > max_length:
        return clean[: max_length - 3].rstrip() + "..."
    return clean


def normalize_action(value: Any) -> str:
    clean = str(value or "").strip().lower()
    return ACTION_ALIASES.get(clean, clean)


def editable_field_map(packet: dict[str, Any]) -> dict[str, str]:
    editable: dict[str, str] = {}
    for item in packet.get("editable_fields") or []:
        if not isinstance(item, dict):
            continue
        key = canonical_field(item.get("key"))
        if key:
            editable[key] = str(item.get("label") or key)
    return editable


def manual_review_target_map(packet: dict[str, Any]) -> dict[str, dict[str, str]]:
    targets: dict[str, dict[str, str]] = {}
    for item in packet.get("manual_review_targets") or []:
        if not isinstance(item, dict):
            continue
        key = canonical_field(item.get("key"))
        if key:
            targets[key] = {
                "key": key,
                "label": str(item.get("label") or key),
                "admin_target_id": str(item.get("admin_target_id") or ""),
            }
    return targets


def allowed_actions(packet: dict[str, Any]) -> list[str]:
    actions = [normalize_action(item) for item in packet.get("allowed_actions") or DECISION_ACTIONS]
    return [item for item in DECISION_ACTIONS if item in actions]


def suggestion_changes(suggestion: dict[str, Any]) -> Any:
    for key in SUGGESTION_CHANGE_KEYS:
        if key in suggestion:
            return suggestion.get(key)
    return {}


def suggestion_manual_target_key(suggestion: dict[str, Any]) -> str:
    for key in SUGGESTION_MANUAL_TARGET_KEYS:
        if key in suggestion and has_value(suggestion.get(key)):
            return canonical_field(suggestion.get(key))
    return ""


def forbidden_control_paths(value: Any, path: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(forbidden_control_paths(item, f"{path}[{index}]"))
        return paths
    if not isinstance(value, dict):
        return paths
    for key, item in value.items():
        key_text = str(key or "").strip()
        child_path = f"{path}.{key_text}" if path else key_text
        if key_text.lower() in FORBIDDEN_CONTROL_KEYS and has_value(item):
            paths.append(child_path)
        paths.extend(forbidden_control_paths(item, child_path))
    return paths


def unexpected_suggestion_keys(suggestion: dict[str, Any]) -> list[str]:
    return sorted(str(key) for key in suggestion if str(key) not in ALLOWED_SUGGESTION_KEYS)


def attention_flags(packet: dict[str, Any], change_keys: list[str]) -> list[str]:
    flags: list[str] = []

    def add(value: str) -> None:
        if value and value not in flags:
            flags.append(value)

    if packet.get("review_type") in HIGH_ATTENTION_REVIEW_TYPES:
        add("review_type_requires_human_attention")
    if packet.get("warnings"):
        add("packet_contains_warnings")
    packet_fields = {
        canonical_field(item.get("key"))
        for item in packet.get("proposed_change") or []
        if isinstance(item, dict)
    }
    changed = {canonical_field(key) for key in change_keys}
    if (packet_fields | changed) & HIGH_ATTENTION_FIELDS:
        add("field_requires_human_attention")
    return flags


def field_safety_errors(key: str, value: Any) -> list[str]:
    clean_key = canonical_field(key)
    errors: list[str] = []
    for message in [phone_warning(clean_key, value), maps_warning(clean_key, value)]:
        if message:
            errors.append(f"unsafe value for {clean_key}: {message}")
    if clean_key == "locations":
        locations = value if isinstance(value, list) else [value]
        for location in locations:
            if not isinstance(location, dict):
                continue
            message = maps_warning("maps_url", location.get("maps_url") or location.get("google_maps_url"))
            if message:
                errors.append(f"unsafe value for locations: {message}")
    return errors


def google_reviews_dependency_errors(
    packet: dict[str, Any],
    action: str,
    change_keys: list[str],
) -> list[str]:
    if action not in {"approve", "modify"}:
        return []
    touches_reviews = "google_reviews_url" in {canonical_field(key) for key in change_keys}
    errors: list[str] = []
    for item in packet.get("proposed_change") or []:
        if not isinstance(item, dict):
            continue
        context = item.get("google_reviews_review")
        if not isinstance(context, dict):
            continue
        dependency = context.get("approval_dependency") or {}
        if not isinstance(dependency, dict):
            dependency = {}
        if dependency.get("satisfied"):
            continue
        if action == "approve" or touches_reviews:
            errors.append(
                "Google reviews require a confirmed clinic Google Maps profile before approval."
            )
    return errors


def validate_suggestion(
    packet: dict[str, Any],
    suggestion: dict[str, Any],
    include_values: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    packet_review_id = str(packet.get("review_id") or "").strip()
    suggestion_review_id = str(suggestion.get("review_id") or "").strip()
    if suggestion_review_id and packet_review_id and suggestion_review_id != packet_review_id:
        errors.append("suggestion review_id does not match the packet")
    for key in unexpected_suggestion_keys(suggestion):
        errors.append(f"unexpected suggestion key is not allowed: {key}")

    action = normalize_action(suggestion.get("action"))
    actions = allowed_actions(packet)
    if not action:
        errors.append("suggestion action is required")
    elif action not in actions:
        errors.append(f"suggestion action must be one of: {', '.join(actions)}")

    raw_changes = suggestion_changes(suggestion)
    if raw_changes is None:
        raw_changes = {}
    if not isinstance(raw_changes, dict):
        errors.append("field changes must be an object")
        raw_changes = {}

    editable = editable_field_map(packet)
    manual_targets = manual_review_target_map(packet)
    manual_target_key = suggestion_manual_target_key(suggestion)
    if manual_target_key and manual_target_key not in manual_targets:
        errors.append(f"manual review target is not allowed in this packet: {manual_target_key}")
    normalized_changes: dict[str, Any] = {}
    for raw_key, value in raw_changes.items():
        key = canonical_field(raw_key)
        if key not in editable:
            errors.append(f"field is not editable in this packet: {key}")
            continue
        normalized_changes[key] = value

    if action in {"approve", "reject"} and normalized_changes:
        errors.append("field changes are only allowed when action is modify")
    if action in {"approve", "reject"} and manual_target_key:
        errors.append("manual review target is only allowed when action is modify")
    if action == "modify" and not normalized_changes:
        if manual_targets:
            if not manual_target_key and len(manual_targets) == 1:
                manual_target_key = next(iter(manual_targets))
            if not manual_target_key:
                errors.append("modify action requires field changes or one manual review target")
        else:
            errors.append("modify action requires at least one editable field change")
    for key, value in normalized_changes.items():
        errors.extend(field_safety_errors(key, value))
    errors.extend(google_reviews_dependency_errors(packet, action, list(normalized_changes)))

    for path in forbidden_control_paths(suggestion):
        errors.append(f"suggestion tries to control a forbidden operation: {path}")

    for warning in as_list(suggestion.get("warnings") or suggestion.get("warnings_to_show")):
        clean = clean_text(warning, include_values=include_values)
        if clean and clean not in warnings:
            warnings.append(clean)

    reason = clean_text(suggestion.get("reason") or suggestion.get("rationale"), include_values=include_values)
    change_keys = list(normalized_changes)
    result = {
        "schema_version": GUARD_SCHEMA_VERSION,
        "valid": not errors,
        "review_id": packet_review_id or suggestion_review_id or None,
        "action": action or None,
        "human_required": True,
        "field_change_keys": change_keys,
        "manual_review_target_key": manual_target_key or None,
        "manual_review_target": manual_targets.get(manual_target_key) if manual_target_key else None,
        "attention_flags": attention_flags(packet, change_keys),
        "reason": reason,
        "warnings": warnings,
        "errors": errors,
        "llm_role": "prepare_suggestions_only",
        "write_policy": "read_only_validation",
    }
    if include_values:
        result["field_changes"] = normalized_changes
    return result


def load_json(path: Path | None) -> Any:
    if path is None or str(path) == "-":
        return json.loads(sys.stdin.read())
    return json.loads(path.read_text(encoding="utf-8"))


def select_packet(data: Any, review_id: str = "") -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("packets"), list):
        packets = [item for item in data["packets"] if isinstance(item, dict)]
        if review_id:
            for packet in packets:
                if str(packet.get("review_id") or "") == review_id:
                    return packet
            raise SystemExit("No packet found for --review-id.")
        if packets:
            return packets[0]
    if isinstance(data, dict):
        return data
    raise SystemExit("Packet input must be a packet object or a report with packets.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-file", type=Path, required=True, help="Decision packet JSON file or report.")
    parser.add_argument("--suggestion-file", type=Path, required=True, help="LLM suggestion JSON file.")
    parser.add_argument("--review-id", default="", help="Packet review_id to select when packet-file is a report.")
    parser.add_argument("--include-values", action="store_true", help="Include accepted field change values in local output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = select_packet(load_json(args.packet_file), review_id=args.review_id)
    suggestion = load_json(args.suggestion_file)
    if not isinstance(suggestion, dict):
        raise SystemExit("Suggestion input must be an object.")
    result = validate_suggestion(packet, suggestion, include_values=args.include_values)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
