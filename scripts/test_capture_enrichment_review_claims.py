#!/usr/bin/env python3
"""Checks for converting enrichment reviews into evidence claims."""

from capture_enrichment_review_claims import field_claims, source_urls


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    payload = {
        "source_urls": [
            "https://clinic.example/about",
            "https://clinic.example/about",
            "https://clinic.example/team",
        ],
        "field_claims": [
            {
                "field_path": "contact.email",
                "value": "info@clinic.example",
                "confidence": 0.8,
                "verifier_verdict": "accepted",
            },
            {
                "field_path": "contact.phone",
                "value": "+34 930 111 222",
                "confidence": 0.5,
                "verifier_verdict": "conflict",
            },
            {
                "field_path": "identity.canonical_name",
                "value": "Clinic was born from a passion for ageing well",
                "confidence": 0.55,
                "verifier_verdict": "rejected",
                "agent_name": "vitalarga-shadow-extractor",
            },
        ],
        "proposed_fields": {
            "summary": "Clinic summary",
            "services": ["VO2 max", "DEXA"],
            "profesionales": ["Dr. Example"],
            "telefono": "+34 930 111 222",
        },
    }
    urls = source_urls(payload)
    claims = field_claims(payload)
    by_path = {claim["field_path"]: claim for claim in claims}

    check(urls == ["https://clinic.example/about", "https://clinic.example/team"], "source URL cleanup failed")
    check(by_path["contact.email"]["verification_status"] == "review", "accepted claims still need review")
    check(by_path["contact.phone"]["verification_status"] == "conflict", "conflict status missing")
    check(by_path["summary"]["value"] == "Clinic summary", "summary mapping missing")
    check(by_path["services.list"]["value"] == ["VO2 max", "DEXA"], "services mapping missing")
    check(by_path["professionals.published"]["value"] == ["Dr. Example"], "professionals mapping missing")
    check("identity.canonical_name" not in by_path, "noisy title identity claim should be suppressed")
    check(len(claims) == 5, "duplicate claim should not be added twice")
    print("OK capture: enrichment review claims")


if __name__ == "__main__":
    main()
