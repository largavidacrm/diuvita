#!/usr/bin/env python3
"""Checks source-backed clinic recommendations become reviewable candidates."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from process_discovery_recommendation_jobs import (
    build_candidate,
    compact_result,
    first_source_url,
    pick_next_source_job,
    peek_next_source_job,
    process_job,
    validate_job,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def fake_fetch(url, timeout=15):
    html = """
<!doctype html>
<html>
<head>
  <title>Tiara Health | Longevity Clinic Marbella</title>
  <meta name="description" content="Tiara Health ofrece programas personalizados de longevidad, medicina preventiva y bienestar en Marbella.">
</head>
<body>
  <h1>Tiara Health</h1>
  <p>Tiara Health ofrece programas personalizados de longevidad, medicina preventiva y bienestar en Marbella.</p>
  <p>Our team of experts includes Dra. Laura García Pérez and Dr. Carlos Martín López.</p>
  <p>Contact: info@tiarahealth.com +34 682 269 673</p>
  <p>Calle Ramón Areces 2, 29660 Marbella</p>
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
    args = Namespace(timeout=15, apply=False)
    public_job = {
        "id": "job-public",
        "job_type": "DISCOVER_CLINIC",
        "input": {
            "mode": "public_recommendation",
            "source": "public_site_recommend_clinic",
            "clinic_name": "Tiara Health",
            "website": "https://www.tiarahealth.com",
            "city": "Marbella",
            "country": "España",
            "requested_info": "specialists",
            "requested_info_label": "Especialistas publicados",
            "note": "Página con equipo visible.",
            "allowed_output": "review_queue_proposal_only",
        },
    }

    result = process_job(public_job, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(result["status"] == "ready", "source-backed recommendation should become ready")
    candidate = result["candidate"]
    check(candidate["name"] == "Tiara Health", "public recommendation name should be preserved")
    check(candidate["website"] == "https://www.tiarahealth.com", "official website should be preserved")
    check(candidate["city"] == "Marbella", "city should be preserved from input")
    check(candidate["country"] == "España", "country should be preserved from input")
    check(candidate["source_url"] == "https://www.tiarahealth.com", "public website should be used as source URL")
    check(candidate["recommendation_context"]["source"] == "public_site_recommend_clinic", "public origin should be visible")
    check(candidate["recommendation_context"]["operator_note"] == "Página con equipo visible.", "note should be preserved")
    check(candidate["recommendation_context"]["allowed_output"] == "review_queue_proposal_only", "review-only contract missing")
    check("professionals" in candidate and len(candidate["professionals"]) == 2, "specialists should be extracted for review")
    check(candidate["review_only"] is True, "candidate should be marked review-only")
    check(0.7 <= candidate["discovery_confidence"] <= 0.82, "confidence should stay review-oriented")

    compact = compact_result(result)
    check(compact["candidate"]["name"] == "Tiara Health", "compact output should keep identity")
    check(compact["candidate"]["field_counts"]["professionals"] == 2, "compact output should show counts")
    check("professionals" not in compact["candidate"], "compact output should not dump proposed specialists")
    check(compact["candidate"]["recommendation_context"]["requested_info_label"] == "Especialistas publicados", "compact context missing")

    admin_job = {
        "id": "job-admin",
        "job_type": "DISCOVER_CLINIC",
        "input": {
            "source": "admin_recommend_clinic_form",
            "source_url": "https://clinic.example/equipo/",
            "operator_note": "Mirar si encaja como clínica nueva.",
            "country": "España",
            "allowed_output": "review_queue_proposal_only",
        },
    }
    check(first_source_url(admin_job["input"]) == "https://clinic.example/equipo/", "admin source URL should be detected")
    admin_result = process_job(admin_job, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(admin_result["candidate"]["recommendation_context"]["source"] == "admin_recommend_clinic_form", "admin origin missing")
    check(admin_result["candidate"]["recommendation_context"]["operator_note"] == "Mirar si encaja como clínica nueva.", "admin note missing")

    source_urls_job = {
        **admin_job,
        "input": {
            "source_urls": ["nota", "https://clinic.example/fuente/"],
            "country": "España",
        },
    }
    check(first_source_url(source_urls_job["input"]) == "https://clinic.example/fuente/", "source_urls should be supported")

    text_only_job = {
        "id": "job-text",
        "job_type": "DISCOVER_CLINIC",
        "input": {
            "source": "admin_recommend_clinic_form",
            "query": "longevity clinic Spain",
            "operator_note": "Buscar clínicas nuevas.",
            "country": "España",
        },
    }
    text_only_result = process_job(text_only_job, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(text_only_result["status"] == "needs_search_provider", "text-only discovery should wait for a search provider")
    check(text_only_result["writes_data"] is False, "text-only discovery should not write")

    calls = []

    def fake_complete(job_id, candidates, admin_email, note, confidence, cost_cents, local_env):
        calls.append((job_id, candidates, admin_email, note, confidence, cost_cents, local_env))
        return {
            "status": "completed",
            "review_items_created": 1,
            "duplicate_review_items_created": 0,
        }

    apply_args = Namespace(timeout=15, apply=True)
    applied = process_job(public_job, apply_args, "admin@example.test", {}, fetcher=fake_fetch, completer=fake_complete)
    check(applied["writes_data"] is True, "apply mode should report a write")
    check(applied["completed_job"]["review_items_created"] == 1, "apply mode should create review cards via existing RPC")
    check(calls and calls[0][0] == "job-public", "complete call should receive job id")
    check(calls and calls[0][1][0]["review_only"] is True, "complete call should receive review-only candidate")
    check("Fuente oficial procesada desde recomendación" in calls[0][3], "operator note should describe source bridge")

    try:
        validate_job({"job_type": "EXTRACT_CLINIC_PROFILE", "input": {}})
    except ValueError as error:
        check("DISCOVER_CLINIC" in str(error), "invalid job type should be explicit")
    else:
        raise AssertionError("invalid job type should fail")

    captured = {}
    original_run_psql = pick_next_source_job.__globals__["run_psql"]
    try:
        def fake_run_psql(sql, local_env):
            captured["sql"] = sql
            return "null"

        pick_next_source_job.__globals__["run_psql"] = fake_run_psql
        picked = pick_next_source_job("admin@example.test", "worker", {})
    finally:
        pick_next_source_job.__globals__["run_psql"] = original_run_psql
    check(picked is None, "empty source-backed queue should return None")
    pick_sql = captured.get("sql", "")
    check("j.job_type = 'DISCOVER_CLINIC'" in pick_sql, "picker should only target discovery jobs")
    check("source_url" in pick_sql and "website" in pick_sql and "source_urls" in pick_sql, "picker should require source-backed input")
    check("source_backed_discovery_job_picked" in pick_sql, "picker should audit source-backed assignment")

    captured_peek = {}
    original_peek_run_psql = peek_next_source_job.__globals__["run_psql"]
    try:
        def fake_peek_run_psql(sql, local_env):
            captured_peek["sql"] = sql
            return "null"

        peek_next_source_job.__globals__["run_psql"] = fake_peek_run_psql
        peeked = peek_next_source_job({})
    finally:
        peek_next_source_job.__globals__["run_psql"] = original_peek_run_psql
    peek_sql = captured_peek.get("sql", "")
    check(peeked is None, "empty source-backed queue peek should return None")
    check("update public.agent_jobs" not in peek_sql.lower(), "peek should not mark a job running")
    check("for update" not in peek_sql.lower(), "peek should be read-only")
    check("j.job_type = 'DISCOVER_CLINIC'" in peek_sql, "peek should only target discovery jobs")

    print("OK discovery recommendations: source-backed jobs become reviewable candidates")


if __name__ == "__main__":
    main()
