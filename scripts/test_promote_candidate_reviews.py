#!/usr/bin/env python3
"""Checks for candidate review promotion gating."""

from promote_candidate_reviews import classify_review, promote_review_sql


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    ready = {
        "id": "review-1",
        "title": "Ready Clinic",
        "payload": {
            "duplicate_probability": 0,
            "candidate": {
                "name": "Ready Clinic",
                "city": "Madrid",
                "country": "España",
                "discovery_confidence": 0.8,
            },
        },
    }
    low_confidence = {
        "id": "review-2",
        "title": "Low Confidence Clinic",
        "payload": {
            "duplicate_probability": 0,
            "candidate": {
                "name": "Low Confidence Clinic",
                "city": "Madrid",
                "country": "España",
                "discovery_confidence": 0.4,
            },
        },
    }
    duplicate = {
        "id": "review-3",
        "title": "Duplicate Clinic",
        "payload": {
            "duplicate_probability": 0.95,
            "candidate": {
                "name": "Duplicate Clinic",
                "city": "Madrid",
                "country": "España",
                "discovery_confidence": 0.95,
            },
        },
    }
    missing = {
        "id": "review-4",
        "title": "Missing City",
        "payload": {
            "duplicate_probability": 0,
            "candidate": {
                "name": "Missing City",
                "country": "España",
                "discovery_confidence": 0.95,
            },
        },
    }

    check(classify_review(ready, 0.55, 0.9)["status"] == "ready", "ready candidate blocked")
    check(classify_review(low_confidence, 0.55, 0.9)["status"] == "hold", "low confidence should wait")
    check(classify_review(duplicate, 0.55, 0.9)["reason"] == "probable_duplicate", "duplicate not blocked")
    check(classify_review(missing, 0.55, 0.9)["reason"] == "missing_city", "missing city not flagged")
    sql = promote_review_sql("00000000-0000-0000-0000-000000000001", "admin@example.com", "note")
    check("admin_create_draft_clinic_from_review_v2" in sql, "draft validation function missing")
    print("OK promote: candidate review gating")


if __name__ == "__main__":
    main()
