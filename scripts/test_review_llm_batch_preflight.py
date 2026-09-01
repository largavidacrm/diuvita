#!/usr/bin/env python3
"""Checks LLM batch preflight stays read-only and one-decision scoped."""
from pathlib import Path

from review_llm_batch_preflight import PREFLIGHT_SCHEMA_VERSION, preflight_report


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def context_ready_row():
    return {
        "id": "ready-1",
        "title": "Revisar extracción shadow: Unidad de Longevidad IMDA",
        "review_type": "clinic_profile_enrichment",
        "priority": 75,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "source_url": "https://imda.example/contacto",
            "from_review_id": "quality-previous",
            "human_supplied_source": True,
            "requested_fields": ["telefono"],
            "requested_field_labels": ["Teléfono principal"],
            "target_scope": "primary_target_first",
            "ui_route": "manual_review_banner_source_handoff",
            "allowed_output": "review_queue_proposal_only",
            "llm_boundary": "respect_source_job_context_scope",
            "proposed_fields": {
                "telefono": "916 000 000",
            },
        },
        "clinic": {
            "id": "clinic-1",
            "slug": "unidad-de-longevidad-imda",
            "display_name": "Unidad de Longevidad IMDA",
            "city": "Madrid",
            "country": "España",
            "status": "preliminary",
            "current_data": {"telefono": "915 111 111"},
        },
    }


def source_without_context_row():
    return {
        "id": "blocked-1",
        "title": "Revisar valoraciones Google: Clinic",
        "review_type": "clinic_profile_enrichment",
        "priority": 60,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "source_url": "https://clinic.example/contacto",
            "proposed_fields": {
                "google_reviews_url": "https://www.google.com/maps/place/Clinic/reviews",
            },
        },
        "clinic": {"display_name": "Clinic", "current_data": {}},
    }


def manual_quality_row():
    return {
        "id": "quality-1",
        "title": "Completar ficha: Tiara Health",
        "review_type": "clinic_quality_audit",
        "priority": 85,
        "created_at": "2026-08-31T12:47:16+00:00",
        "payload": {
            "issues": [
                {"code": "missing_professionals", "label": "Faltan especialistas publicados"},
            ],
        },
        "clinic": {
            "id": "clinic-tiara",
            "slug": "tiara-health",
            "display_name": "Tiara Health",
            "city": "Marbella",
            "country": "España",
            "status": "preliminary",
            "current_data": {},
        },
    }


def main():
    rows = [context_ready_row(), source_without_context_row(), manual_quality_row()]
    report = preflight_report(rows)
    items = {item["review_id"]: item for item in report["items"]}

    check(report["schema_version"] == PREFLIGHT_SCHEMA_VERSION, "schema version missing")
    check(report["writes_data"] is False, "preflight must not write data")
    check(report["calls_llm"] is False, "preflight must not call an LLM")
    check(report["decision_scope"] == "one_card_one_decision", "decision scope missing")
    check(report["summary"]["total_packets"] == 3, "total packet count missing")
    check(report["summary"]["reported_packets"] == 3, "reported packet count missing")
    check(report["summary"]["llm_ready"] == 2, "ready count missing")
    check(report["summary"]["blocked"] == 1, "blocked count missing")
    check(report["summary"]["source_without_context"] == 1, "source-only count missing")
    check(report["summary"]["manual_review_target_packets"] == 1, "manual target count missing")

    ready = items["ready-1"]
    check(ready["strict_prompt_status"] == "ready", "context-ready packet should pass strict prompt preflight")
    check(ready["prompt_schema_version"] == "review_decision_llm_prompt.v1", "prompt schema marker missing")
    check(ready["prompt_write_policy"] == "no_writes", "prompt write policy missing")
    check(ready["expected_actions"] == ["approve", "reject", "modify"], "expected action contract missing")

    blocked = items["blocked-1"]
    check(blocked["strict_prompt_status"] == "blocked", "source-only packet should be blocked")
    check(blocked["llm_ready"] is False, "blocked packet should not be LLM-ready")
    check("source_without_context" in blocked["blocked_reason"], "blocked reason should explain source-only context")
    check(blocked["next_step"] == "human_review_or_source_handoff", "blocked next step missing")

    manual = items["quality-1"]
    check(manual["strict_prompt_status"] == "ready", "manual target packet should produce a safe prompt")
    check(manual["manual_review_targets"] == ["profesionales"], "manual target key missing")
    check(manual["clinic_name"] == "Tiara Health", "manual clinic name missing")

    ready_only = preflight_report(rows, llm_ready_only=True)
    check(ready_only["summary"]["total_packets"] == 3, "ready-only should keep original total")
    check(ready_only["summary"]["reported_packets"] == 2, "ready-only should report only strict-ready packets")
    check(all(item["llm_ready"] for item in ready_only["items"]), "ready-only report should not include blocked items")

    source = (ROOT / "scripts" / "review_llm_batch_preflight.py").read_text(encoding="utf-8")
    check("--fail-if-blocked" in source, "CLI should offer a blocking preflight mode")
    check("admin_update_clinic" not in source, "preflight script must not contain write hooks")
    print("OK review LLM batch preflight: strict-ready batches stay safe")


if __name__ == "__main__":
    main()
