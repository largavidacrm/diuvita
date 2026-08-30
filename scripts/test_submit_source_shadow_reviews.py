#!/usr/bin/env python3
"""Checks for safe batch shadow reviews from existing clinic sources."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from submit_source_shadow_reviews import load_clinic_sources, process_source, process_sources, summarize_results


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def fake_fetch(url, timeout=15):
    html = """
<!doctype html>
<html>
<head><title>Example Longevity Clinic</title></head>
<body>
  <p>Medicina preventiva, longevidad and VO2 max.</p>
  <p>Unidad de Longevidad con Dra. Laura García Pérez.</p>
  <p>Contact: info@exampleclinic.test</p>
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
    source = {
        "source_record_id": "source-1",
        "clinic_id": "clinic-1",
        "clinic_slug": "example-clinic",
        "clinic_name": "Example Clinic",
        "source_url": "https://exampleclinic.test/longevity",
        "pending_count": 3,
        "pending_fields": ["contact", "specialists", "technology"],
        "has_open_review": False,
        "has_open_clinic_review": False,
    }
    args = Namespace(timeout=15, apply=False, replace_existing=False, allow_multiple_open_clinic_reviews=False)
    result = process_source(source, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(result["status"] == "ready", "source should produce a ready review payload")
    check("email" in result["proposed_fields"], "email proposal missing")
    check("profesionales" in result["proposed_fields"], "professional proposal missing")
    check(result["pending_count"] == 3, "pending-count context should be preserved")
    check("specialists" in result["pending_fields"], "pending-field context should be preserved")

    skipped = process_source(
        dict(source, has_open_review=True),
        args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(skipped["status"] == "skipped", "existing open review should be skipped by default")
    check("already exists" in skipped["reason"], "skip reason should be readable")

    clinic_skipped = process_source(
        dict(source, has_open_clinic_review=True),
        args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(clinic_skipped["status"] == "skipped", "existing clinic review should be skipped by default")
    check("for this clinic" in clinic_skipped["reason"], "clinic skip reason should be readable")

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
        return {"status": "inserted", "id": "review-1"}

    apply_args = Namespace(timeout=15, apply=True, replace_existing=True, allow_multiple_open_clinic_reviews=False)
    applied = process_source(
        dict(source, has_open_review=True),
        apply_args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
        review_creator=fake_create_review,
    )
    check(applied["created_review"]["status"] == "inserted", "apply mode should create a review")
    check(calls and calls[0][3] is True, "replace_existing should pass through")
    check(calls and calls[0][4] is False, "clinic duplicate guard should pass through")

    batch_args = Namespace(timeout=15, apply=False, replace_existing=False, allow_multiple_open_clinic_reviews=False)
    batch = process_sources(
        [
            dict(source, source_record_id="source-1", source_url="https://exampleclinic.test/one"),
            dict(source, source_record_id="source-2", source_url="https://exampleclinic.test/two"),
        ],
        batch_args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(batch[0]["status"] == "ready", "first source in batch should run")
    check(batch[1]["status"] == "skipped", "second source for same clinic should be skipped")
    check("already queued" in batch[1]["reason"], "same-batch skip reason should be readable")

    summary = summarize_results([result, skipped, applied])
    check(summary["sources_seen"] == 3, "summary source count missing")
    check(summary["ready"] == 2, "summary ready count missing")
    check(summary["skipped"] == 1, "summary skipped count missing")
    check(summary["created_or_updated"] == 1, "summary created count missing")

    captured = {}

    def fake_run_psql(sql, local_env):
        captured["sql"] = sql
        return "[]"

    original_run_psql = load_clinic_sources.__globals__["run_psql"]
    try:
        load_clinic_sources.__globals__["run_psql"] = fake_run_psql
        load_clinic_sources(5, None, None, {})
    finally:
        load_clinic_sources.__globals__["run_psql"] = original_run_psql

    sql = captured.get("sql", "")
    check("pending_fields" in sql, "source batch should measure missing public fields")
    check("jsonb_agg(to_jsonb(items) order by items.pending_count desc" in sql, "source batch output should preserve priority order")
    check("cardinality(candidate.pending_fields) desc" in sql, "source batch should prioritize incomplete profiles")
    check("has_open_review asc" in sql, "source batch should prefer sources without open review cards")
    print("OK source shadow reviews: batch is safe")


if __name__ == "__main__":
    main()
