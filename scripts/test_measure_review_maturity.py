#!/usr/bin/env python3
"""Checks for the read-only review maturity measurement."""

from measure_review_maturity import format_measurement, maturity_status, review_target


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_measurement():
    return {
        "generated_at": "2026-08-30T10:20:00+00:00",
        "summary": {
            "clinics": {"total": 20, "published": 11, "preliminary": 8, "draft": 1},
            "automation": {"shadow_review_target": 200},
        },
        "reviews_by_type": [
            {
                "review_type": "candidate_clinic",
                "total": 4,
                "open": 2,
                "resolved": 1,
                "dismissed": 1,
            },
            {
                "review_type": "clinic_quality_audit",
                "total": 3,
                "open": 3,
                "resolved": 0,
                "dismissed": 0,
            },
        ],
        "claims_by_status": [
            {"verification_status": "proposed", "total": 12},
            {"verification_status": "conflict", "total": 1},
        ],
        "claims_by_field": [
            {"field_path": "services.list", "total": 7, "needs_review": 7},
        ],
        "blocked_claims": [
            {
                "clinic_name": "Clinic",
                "clinic_slug": "clinic",
                "field_path": "services.list",
                "verification_status": "conflict",
                "confidence": 0.82,
                "source_record_id": "source-1",
            }
        ],
        "source_coverage": {
            "source_records": 9,
            "source_snapshots": 5,
            "claims_with_source": 12,
            "claims_without_source": 1,
        },
        "jobs_7d": {"total": 2, "completed": 2, "queued": 0, "running": 0, "failed": 0},
    }


def main():
    measurement = sample_measurement()
    status = maturity_status(measurement, 200)
    output = format_measurement(measurement, review_target(measurement, None))
    check(status["ready_for_low_risk_autopublish"] is False, "should not be ready with small sample")
    check(status["completed_candidate_reviews"] == 2, "candidate decisions not counted")
    check(review_target(measurement, None) == 200, "target should come from automation summary")
    check(review_target(measurement, 50) == 50, "explicit target should win")
    check("# Vitalarga review maturity" in output, "title missing")
    check("Low-risk auto-publish readiness: not ready" in output, "decision missing")
    check("clinicas candidatas: 2/4 closed" in output, "candidate review summary missing")
    check("## Blocking claims" in output, "blocking claims section missing")
    check("Clinic | services.list: conflict, 82%, con fuente" in output, "blocking claim detail missing")
    check("Source snapshots: 5" in output, "source coverage missing")
    check("services.list: 7 total" in output, "field grouping missing")
    print("OK maturity: review measurement")


if __name__ == "__main__":
    main()
