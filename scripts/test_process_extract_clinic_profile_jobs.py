#!/usr/bin/env python3
"""Checks queued EXTRACT_CLINIC_PROFILE jobs become bounded review proposals."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from process_extract_clinic_profile_jobs import (
    build_payload_for_job,
    compact_result,
    filter_proposed_fields_for_request,
    process_job,
    requested_targets,
    validate_job,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def fake_fetch(url, timeout=15):
    html = """
<!doctype html>
<html>
<head><title>Tiara Health experts</title></head>
<body>
  <h1>Our team of experts</h1>
  <p>Unidad de Longevidad y medicina regenerativa.</p>
  <p>Dra. Laura García Pérez, especialista en medicina preventiva.</p>
  <p>Dr. Carlos Martín López, medicina estética y regenerativa.</p>
  <p>Contact: team@exampleclinic.test</p>
</body>
</html>
""".encode("utf-8")
    return FetchResult(
        source_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=html,
    )


def main():
    job = {
        "id": "job-1",
        "job_type": "EXTRACT_CLINIC_PROFILE",
        "clinic_id": "clinic-1",
        "input": {
            "mode": "shadow",
            "clinic_id": "clinic-1",
            "clinic_slug": "tiara-health",
            "clinic_name": "Tiara Health",
            "source_url": "https://www.tiarahealth.com/our-team-of-experts/",
            "requested_fields": ["profesionales", "unidades"],
            "requested_field_labels": ["Especialistas publicados", "Unidades"],
            "missing_fields": ["Especialistas publicados", "Unidades"],
            "from_review_id": "review-1",
            "human_supplied_source": True,
            "source_job_version": "2026-08-31.manual-review-source",
            "operator_intent": "Daniel indica que esta URL oficial contiene especialistas.",
            "allowed_output": "review_queue_proposal_only",
        },
    }
    args = Namespace(
        timeout=15,
        apply=False,
        replace_existing=False,
        allow_multiple_open_clinic_reviews=False,
    )

    result = process_job(job, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(result["status"] == "ready", "team source should produce a reviewable proposal")
    check(result["clinic_slug"] == "tiara-health", "clinic slug should pass through")
    check(result["source_url"].endswith("/our-team-of-experts/"), "source URL should pass through")
    check(result["requested_fields"] == ["profesionales", "unidades"], "requested fields should be preserved")
    check(result["missing_fields"] == ["Especialistas publicados", "Unidades"], "missing labels should be preserved")
    check("profesionales" in result["proposed_fields"], "professionals should be proposed")
    check("unidades" in result["proposed_fields"], "units should be proposed")
    check("email" not in result["proposed_fields"], "unrequested contact should not be proposed")
    check(result["proposed_field_counts"]["profesionales"] >= 1, "professional count should be visible")

    payload = build_payload_for_job(job, {
        "verified_claims": [],
        "rule_decisions": [],
        "summary": {},
        "source_url": "https://www.tiarahealth.com/our-team-of-experts/",
    })
    check(payload["from_review_id"] == "review-1", "review link should stay in payload")
    check(payload["requested_fields"] == ["profesionales", "unidades"], "payload should keep requested fields")
    check(payload["requested_field_labels"] == ["Especialistas publicados", "Unidades"], "payload should keep requested labels")
    check(payload["human_supplied_source"] is True, "payload should mark human-supplied source URLs")
    check(payload["operator_intent"].startswith("Daniel indica"), "payload should preserve operator intent")
    check(payload["allowed_output"] == "review_queue_proposal_only", "payload should preserve proposal-only contract")
    check("No edita la ficha ni publica datos" in " ".join(payload["warnings"]), "payload should keep safety warning")

    calls = []

    def fake_create_review(
        clinic_slug,
        payload,
        admin_email,
        local_env,
        replace_existing,
        allow_multiple_open_clinic_reviews,
    ):
        calls.append((clinic_slug, payload, admin_email, replace_existing, allow_multiple_open_clinic_reviews))
        return {"status": "inserted", "id": "review-new"}

    apply_args = Namespace(
        timeout=15,
        apply=True,
        replace_existing=True,
        allow_multiple_open_clinic_reviews=True,
    )
    applied = process_job(job, apply_args, "admin@example.test", {}, fetcher=fake_fetch, review_creator=fake_create_review)
    check(applied["created_review"]["status"] == "inserted", "apply mode should create a review")
    check(applied["writes_data"] is True, "apply mode should report a write")
    check(calls and calls[0][0] == "tiara-health", "review creator should receive clinic slug")
    check(calls and calls[0][3] is True, "replace flag should pass through")
    check(calls and calls[0][4] is True, "multiple-open flag should pass through")
    check(calls and calls[0][1]["from_review_id"] == "review-1", "created review should trace source review")

    compact = compact_result(applied)
    check("verification_summary" not in compact, "compact result should omit verification details")
    check(compact["writes_data"] is True, "compact result should keep write signal")
    check(compact["created_review"]["id"] == "review-new", "compact result should keep created review id")

    check(requested_targets(["specialists", "technology"]) == {"profesionales", "tech"}, "aliases should map to UI fields")
    check(
        filter_proposed_fields_for_request(
            {"email": "x@example.test", "profesionales": ["A"], "tech": "X"},
            ["profesionales"],
        ) == {"profesionales": ["A"]},
        "requested fields should bound proposals",
    )

    invalid = dict(job, input={})
    try:
        validate_job(invalid)
    except Exception as error:
        check("clinic_slug" in str(error), "invalid jobs should explain missing clinic slug")
    else:
        raise AssertionError("invalid job should fail validation")

    print("OK extract profile jobs: queued source URLs become bounded review proposals")


if __name__ == "__main__":
    main()
