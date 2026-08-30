#!/usr/bin/env python3
"""Basic checks for the deterministic Vitalarga rules engine."""
from vitalarga_rules import RiskPolicy, decide_claim, field_risk


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    check(field_risk("contact.email") == "low", "email should be low risk")
    check(field_risk("services.list") == "medium", "services should be medium risk")
    check(field_risk("specialties.list") == "medium", "specialties should be medium risk")
    check(field_risk("units.list") == "medium", "units should be medium risk")
    check(field_risk("professionals.published") == "medium", "published specialists should be medium risk")
    check(field_risk("transparency.specialists_count") == "medium", "specialist count should be medium risk")
    check(field_risk("team.credentialing_visible") == "high", "credentialing visibility should be high risk")
    check(field_risk("prices.public_status") == "high", "public pricing status should be high risk")
    check(field_risk("prices.initial_consultation") == "high", "prices should be high risk")
    check(field_risk("unknown.field") == "high", "unknown fields should default high")

    accepted_low = {
        "field_path": "contact.email",
        "confidence": 0.96,
        "verifier_verdict": "accepted",
        "source_count": 1,
    }
    check(decide_claim(accepted_low)["action"] == "review", "auto-publish off should review")
    check(
        decide_claim(accepted_low, RiskPolicy(auto_publish_enabled=True))["action"] == "auto_accept",
        "low-risk claim should auto-accept when enabled",
    )

    medium = {
        "field_path": "services.list",
        "confidence": 0.97,
        "verifier_verdict": "accepted",
        "source_count": 1,
    }
    check(
        decide_claim(medium, RiskPolicy(auto_publish_enabled=True))["action"] == "review",
        "medium risk should stay in review by default",
    )

    high_one_source = {
        "field_path": "prices.initial_consultation",
        "confidence": 0.99,
        "verifier_verdict": "accepted",
        "source_count": 1,
    }
    check(
        decide_claim(high_one_source, RiskPolicy(auto_publish_enabled=True, high_auto_publish_enabled=True))["action"] == "review",
        "high risk should require multiple sources",
    )

    rejected = {
        "field_path": "contact.phone",
        "confidence": 0.95,
        "verifier_verdict": "rejected",
        "source_count": 1,
    }
    check(decide_claim(rejected)["action"] == "reject", "rejected verdict should reject")

    locked = {
        "field_path": "contact.phone",
        "confidence": 0.99,
        "verifier_verdict": "accepted",
        "source_count": 2,
        "human_locked": True,
    }
    check(decide_claim(locked)["action"] == "review", "human lock should force review")

    print("OK rules: deterministic publication decisions")


if __name__ == "__main__":
    main()
