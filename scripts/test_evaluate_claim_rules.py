#!/usr/bin/env python3
"""Checks for read-only evaluation of stored field claims."""
from diuvita_rules import RiskPolicy
from evaluate_claim_rules import evaluate_rows, format_report, policy_from_automation, summarize


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    rows = [
        {
            "id": "claim-a",
            "clinic_slug": "clinic-a",
            "clinic_name": "Clinic A",
            "field_path": "contact.website",
            "confidence": 0.96,
            "verification_status": "accepted",
            "source_record_id": "source-a",
            "human_locked": False,
        },
        {
            "id": "claim-b",
            "clinic_slug": "clinic-a",
            "clinic_name": "Clinic A",
            "field_path": "services.list",
            "confidence": 0.96,
            "verification_status": "accepted",
            "source_record_id": "source-b",
            "human_locked": False,
        },
        {
            "id": "claim-c",
            "clinic_slug": "clinic-b",
            "clinic_name": "Clinic B",
            "field_path": "contact.phone",
            "confidence": 0.42,
            "verification_status": "accepted",
            "source_record_id": "source-c",
            "human_locked": False,
        },
    ]
    current_policy = policy_from_automation({"auto_publish_enabled": False}, False)
    current = evaluate_rows(rows, current_policy)
    current_summary = summarize(current)
    check(current_summary["actions"]["review"] == 2, "current policy should keep accepted claims in review")
    check(current_summary["actions"]["reject"] == 1, "low-confidence claim should be rejected")

    preview_policy = policy_from_automation({"auto_publish_enabled": False}, True)
    preview = evaluate_rows(rows, preview_policy)
    preview_summary = summarize(preview)
    check(preview_summary["actions"]["auto_accept"] == 1, "preview should auto-accept the low-risk sourced claim")
    check(preview_summary["actions"]["review"] == 1, "medium-risk claims should stay in review")
    check(preview_summary["risks"]["low"] == 2, "low-risk count missing")

    report = format_report(preview, "low-risk auto-publish preview")
    check("Database writes: none" in report, "read-only guarantee missing")
    check("Public changes: none" in report, "public no-change guarantee missing")
    check("contact.website" in report, "sample decision missing")
    check(isinstance(current_policy, RiskPolicy), "policy builder should return RiskPolicy")
    print("OK claim rules: stored-claim evaluation")


if __name__ == "__main__":
    main()
