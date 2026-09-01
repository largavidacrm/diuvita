#!/usr/bin/env python3
"""Checks queued EXTRACT_CLINIC_PROFILE jobs become bounded review proposals."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from process_extract_clinic_profile_jobs import (
    build_payload_for_job,
    compact_result,
    complete_job,
    created_review_replaces_origin,
    filter_proposed_fields_for_request,
    process_job,
    requested_targets,
    review_source_job_should_replace_existing_reviews,
    source_job_origin_review_id,
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


def fake_fetch_summary(url, timeout=15):
    html = """
<!doctype html>
<html>
<head>
  <title>Tiara Health Takes Health Management to The Next Level</title>
  <meta name="description" content="Tiara Health ofrece tratamientos a medida y programas personalizados diseñados para adaptarse a sus retos y necesidades de salud.">
</head>
<body>
  <p>Contact: info@tiarahealth.com +34 682 269 673</p>
  <p>Tiara Health ofrece tratamientos a medida y programas personalizados diseñados para adaptarse a sus retos y necesidades de salud.</p>
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
            "primary_requested_fields": ["profesionales"],
            "primary_requested_field_labels": ["Especialistas publicados"],
            "target_scope": "primary_target_first",
            "ui_route": "manual_review_banner_source_handoff",
            "missing_fields": ["Especialistas publicados", "Unidades"],
            "from_review_id": "review-1",
            "human_supplied_source": True,
            "source_job_version": "2026-08-31.manual-review-source",
            "operator_intent": "Daniel indica que esta URL oficial contiene especialistas.",
            "operator_requested_field_summary": "especialistas publicados, unidades",
            "llm_boundary": "respect_source_job_context_scope",
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
    check(result["primary_requested_fields"] == ["profesionales"], "primary requested field should be preserved")
    check(result["target_scope"] == "primary_target_first", "target scope should be preserved")
    check(result["ui_route"] == "manual_review_banner_source_handoff", "UI route should be preserved")
    check(result["missing_fields"] == ["Especialistas publicados", "Unidades"], "missing labels should be preserved")
    check("profesionales" in result["proposed_fields"], "professionals should be proposed")
    check("unidades" in result["proposed_fields"], "units should be proposed")
    check("email" not in result["proposed_fields"], "unrequested contact should not be proposed")
    check(result["proposed_field_counts"]["profesionales"] >= 1, "professional count should be visible")

    summary_job = {
        **job,
        "id": "job-summary",
        "input": {
            **job["input"],
            "source_url": "https://www.tiarahealth.com/about-tiara-health/",
            "requested_fields": ["summary"],
            "requested_field_labels": ["Resumen"],
            "primary_requested_fields": ["summary"],
            "primary_requested_field_labels": ["Resumen"],
            "missing_fields": ["Resumen"],
            "operator_requested_field_keys": ["summary"],
            "operator_requested_field_labels": ["Resumen"],
            "operator_requested_field_summary": "resumen",
        },
    }
    summary_result = process_job(summary_job, args, "admin@example.test", {}, fetcher=fake_fetch_summary)
    check(summary_result["status"] == "ready", "summary source should produce a reviewable proposal")
    check(summary_result["proposed_fields"] == ["summary"], "summary job should only propose the requested summary")

    payload = build_payload_for_job(job, {
        "verified_claims": [],
        "rule_decisions": [],
        "summary": {},
        "source_url": "https://www.tiarahealth.com/our-team-of-experts/",
    })
    check(payload["from_review_id"] == "review-1", "review link should stay in payload")
    check(payload["requested_fields"] == ["profesionales", "unidades"], "payload should keep requested fields")
    check(payload["requested_field_labels"] == ["Especialistas publicados", "Unidades"], "payload should keep requested labels")
    check(payload["primary_requested_fields"] == ["profesionales"], "payload should keep primary requested fields")
    check(payload["primary_requested_field_labels"] == ["Especialistas publicados"], "payload should keep primary requested labels")
    check(payload["operator_requested_field_keys"] == ["profesionales", "unidades"], "payload should keep operator requested field keys")
    check(payload["operator_requested_field_labels"] == ["Especialistas publicados", "Unidades"], "payload should keep operator requested labels")
    check(payload["operator_requested_field_summary"] == "especialistas publicados, unidades", "payload should keep operator requested summary")
    check(payload["target_scope"] == "primary_target_first", "payload should keep target scope")
    check(payload["ui_route"] == "manual_review_banner_source_handoff", "payload should keep UI route")
    check(payload["human_supplied_source"] is True, "payload should mark human-supplied source URLs")
    check(payload["operator_intent"].startswith("Daniel indica"), "payload should preserve operator intent")
    check(payload["llm_boundary"] == "respect_source_job_context_scope", "payload should keep LLM boundary")
    check(payload["allowed_output"] == "review_queue_proposal_only", "payload should preserve proposal-only contract")
    check("No edita la ficha ni publica datos" in " ".join(payload["warnings"]), "payload should keep safety warning")
    check(source_job_origin_review_id(job) == "review-1", "origin review id should be readable")
    check(
        review_source_job_should_replace_existing_reviews(job) is True,
        "review-supplied source jobs should replace stale open review cards",
    )
    check(created_review_replaces_origin({"status": "updated_clinic"}) is True, "updated clinic card should supersede origin")
    check(created_review_replaces_origin({"status": "existing_clinic"}) is False, "unchanged card should not supersede origin")

    calls = []
    superseded = []

    def fake_create_review(
        clinic_slug,
        payload,
        admin_email,
        local_env,
        replace_existing,
        allow_multiple_open_clinic_reviews,
        replace_existing_clinic_review,
    ):
        calls.append((
            clinic_slug,
            payload,
            admin_email,
            replace_existing,
            allow_multiple_open_clinic_reviews,
            replace_existing_clinic_review,
        ))
        return {"status": "inserted", "id": "review-new"}

    def fake_supersede_origin(job, created_review, admin_email, local_env):
        superseded.append((job["id"], created_review["id"], admin_email))
        return {"id": "review-1", "status": "resolved"}

    apply_args = Namespace(
        timeout=15,
        apply=True,
        replace_existing=True,
        allow_multiple_open_clinic_reviews=True,
    )
    applied = process_job(
        job,
        apply_args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
        review_creator=fake_create_review,
        origin_review_resolver=fake_supersede_origin,
    )
    check(applied["created_review"]["status"] == "inserted", "apply mode should create a review")
    check(applied["writes_data"] is True, "apply mode should report a write")
    check(calls and calls[0][0] == "tiara-health", "review creator should receive clinic slug")
    check(calls and calls[0][3] is True, "replace flag should pass through")
    check(calls and calls[0][4] is True, "multiple-open flag should pass through")
    check(calls and calls[0][5] is True, "manual source jobs should refresh existing clinic review cards")
    check(calls and calls[0][1]["from_review_id"] == "review-1", "created review should trace source review")
    check(calls and calls[0][1]["target_scope"] == "primary_target_first", "created review should keep source scope")
    check(applied["superseded_review"]["status"] == "resolved", "origin manual review should be superseded")
    check(superseded and superseded[0][0] == "job-1", "origin resolver should receive the source job")

    compact = compact_result(applied)
    check("verification_summary" not in compact, "compact result should omit verification details")
    check(compact["writes_data"] is True, "compact result should keep write signal")
    check(compact["created_review"]["id"] == "review-new", "compact result should keep created review id")
    check(compact["superseded_review"]["id"] == "review-1", "compact result should keep superseded origin id")
    check(compact["primary_requested_fields"] == ["profesionales"], "compact result should keep primary requested fields")
    check(compact["target_scope"] == "primary_target_first", "compact result should keep source scope")

    captured_complete = {}
    original_run_psql = complete_job.__globals__["run_psql"]
    try:
        def fake_complete_run_psql(sql, local_env):
            captured_complete["sql"] = sql
            return '{"id": "00000000-0000-0000-0000-000000000001", "status": "completed"}'

        complete_job.__globals__["run_psql"] = fake_complete_run_psql
        complete_job("00000000-0000-0000-0000-000000000001", compact, "admin@example.test", {})
    finally:
        complete_job.__globals__["run_psql"] = original_run_psql
    complete_sql = captured_complete.get("sql", "")
    check("cross join claims" in complete_sql, "complete job should execute admin claims CTE")
    check("current_setting('request.jwt.claims'" not in complete_sql, "complete job should not parse possibly empty claims")
    check("origin_review_superseded" in complete_sql, "complete event should record origin supersession")

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
