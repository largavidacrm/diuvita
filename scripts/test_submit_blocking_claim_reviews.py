#!/usr/bin/env python3
"""Checks for blocking-claim review card creation."""

from submit_blocking_claim_reviews import create_review_sql, issue_label, priority_for_claims, review_payload


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_group():
    return {
        "clinic_id": "00000000-0000-0000-0000-000000000001",
        "clinic_slug": "clinic",
        "clinic_name": "Clinic",
        "clinic_city": "Barcelona",
        "clinic_country": "España",
        "website": "https://clinic.example",
        "claims": [
            {
                "claim_id": "claim-1",
                "field_path": "identity.canonical_name",
                "verification_status": "rejected",
                "blocker_status": "rejected",
                "confidence": 0.55,
                "source_record_id": "source-1",
                "source_url": "https://clinic.example",
            },
            {
                "claim_id": "claim-2",
                "field_path": "contact.phone",
                "verification_status": "review",
                "blocker_status": "without_source",
                "confidence": 0.60,
                "source_record_id": None,
                "source_url": None,
            },
        ],
    }


def main():
    group = sample_group()
    payload = review_payload(group)
    sql = create_review_sql(group, "admin@example.com")

    check(priority_for_claims(group["claims"]) == 85, "rejected claim should be high priority")
    check(issue_label(group["claims"][0]) == "Claim rechazado: identity.canonical_name", "rejected label missing")
    check(issue_label(group["claims"][1]) == "Claim sin fuente: contact.phone", "without-source label missing")
    check(payload["quality_context"] == "blocking_claims", "quality context missing")
    check(payload["mode"] == "shadow", "review should be shadow mode")
    check(len(payload["issues"]) == 2, "issues should mirror blocking claims")
    check("clinic_quality_audit" in sql, "review type should reuse quality audits")
    check("field_claims" in sql, "field path should point to field claims")
    check("public.clinics" in sql and "public.review_queue" in sql, "expected tables missing")
    check("admin_update_clinic" not in sql, "tool must not edit clinic profiles")
    check("published" not in sql, "tool must not publish clinics")
    print("OK blocking claims: internal review card")


if __name__ == "__main__":
    main()
