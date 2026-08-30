#!/usr/bin/env python3
"""Checks for processing source-change cards into review proposals."""
from process_source_change_reviews import (
    enrichment_payload_for_change,
    source_change_input,
    summarize_results,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    row = {
        "id": "review-1",
        "clinic_id": "clinic-id",
        "payload": {
            "clinic_slug": "clinic-a",
            "clinic_name": "Clinic A",
            "source_url": "https://clinic.example",
            "material_hints": [{"area": "contact", "label": "Contacto", "terms": ["telefono"]}],
            "material_summary": "Contacto",
        },
    }
    change = source_change_input(row)
    check(change["clinic_slug"] == "clinic-a", "clinic slug missing")
    check(change["source_url"] == "https://clinic.example", "source url missing")
    check(change["material_summary"] == "Contacto", "material summary missing")

    verification = {
        "source_url": "https://clinic.example",
        "verified_claims": [
            {
                "field_path": "contact.phone",
                "value": "+34 600 000 000",
                "verifier_verdict": "accepted",
                "verifier_confidence": 0.94,
                "source_url": "https://clinic.example",
            }
        ],
        "rule_decisions": [
            {"field_path": "contact.phone", "action": "review", "risk": "low", "confidence": 0.94}
        ],
        "summary": {"claims": 1},
    }
    payload = enrichment_payload_for_change(change, verification)
    check(payload["source_change_review_id"] == "review-1", "source review link missing")
    check(payload["source_change_material_summary"] == "Contacto", "material context missing")
    check("telefono" in str(payload["source_change_material_hints"]), "material hint terms missing")
    check(payload["warnings"][0].startswith("Fuente vigilada modificada"), "source-change warning missing")

    summary = summarize_results([
        {"status": "ready"},
        {"status": "empty"},
        {"status": "skipped"},
        {"status": "failed"},
    ])
    check(summary == {"reviews_seen": 4, "ready": 1, "empty": 1, "skipped": 1, "failed": 1}, "summary counts wrong")
    print("OK source change processing: proposal bridge")


if __name__ == "__main__":
    main()
