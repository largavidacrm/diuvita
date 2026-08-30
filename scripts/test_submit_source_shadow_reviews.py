#!/usr/bin/env python3
"""Checks for safe batch shadow reviews from existing clinic sources."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from submit_source_shadow_reviews import (
    compact_output,
    load_clinic_sources,
    process_source,
    process_sources,
    proposed_field_counts,
    summarize_results,
)


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
        "source_type": "website",
        "pending_count": 3,
        "pending_fields": ["contact", "specialists", "technology"],
        "specialists_pending": True,
        "team_source_priority": 0,
        "has_open_review": False,
        "has_open_clinic_review": False,
        "open_review": None,
        "open_clinic_review": None,
    }
    args = Namespace(timeout=15, apply=False, replace_existing=False, allow_multiple_open_clinic_reviews=False)
    result = process_source(source, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(result["status"] == "ready", "source should produce a ready review payload")
    check("email" in result["proposed_fields"], "email proposal missing")
    check("profesionales" in result["proposed_fields"], "professional proposal missing")
    check(result["proposed_field_counts"]["profesionales"] == 1, "professional count should be visible")
    check(result["pending_count"] == 3, "pending-count context should be preserved")
    check("specialists" in result["pending_fields"], "pending-field context should be preserved")
    check(result["specialists_pending"] is True, "specialist priority context should be preserved")
    check(result["team_source_priority"] == 0, "team source priority should be preserved")

    skipped = process_source(
        dict(source, has_open_review=True, open_review={"id": "review-source-1", "title": "Open source review"}),
        args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(skipped["status"] == "skipped", "existing open review should be skipped by default")
    check("already exists" in skipped["reason"], "skip reason should be readable")
    check(skipped["open_review"]["title"] == "Open source review", "source skip should explain existing review")

    clinic_skipped = process_source(
        dict(source, has_open_clinic_review=True, open_clinic_review={"id": "review-clinic-1", "title": "Open clinic review"}),
        args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(clinic_skipped["status"] == "skipped", "existing clinic review should be skipped by default")
    check("for this clinic" in clinic_skipped["reason"], "clinic skip reason should be readable")
    check(clinic_skipped["open_clinic_review"]["title"] == "Open clinic review", "clinic skip should explain existing review")

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
            dict(
                source,
                source_record_id="source-2",
                source_type="official_team_page",
                source_url="https://exampleclinic.test/equipo-medico",
                team_source_priority=1,
            ),
        ],
        batch_args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(batch[0]["status"] == "ready", "first source in batch should run")
    check(batch[1]["status"] == "skipped", "second source for same clinic should be skipped")
    check("already queued" in batch[1]["reason"], "same-batch skip reason should be readable")
    check(batch[1]["source_type"] == "official_team_page", "same-batch skip should preserve source type")
    check(batch[1]["team_source_priority"] == 1, "same-batch skip should preserve team priority")

    summary = summarize_results([result, skipped, applied])
    check(summary["sources_seen"] == 3, "summary source count missing")
    check(summary["ready"] == 2, "summary ready count missing")
    check(summary["skipped"] == 1, "summary skipped count missing")
    check(summary["created_or_updated"] == 1, "summary created count missing")
    compact = compact_output({"mode": "dry_run", **summary, "items": [result, skipped, dict(result, status="failed", error="timeout")]})
    check(compact["writes_data"] is False, "compact dry run should be read-only")
    check(len(compact["ready_items"]) == 1, "compact output should keep ready items")
    check(len(compact["skipped_items"]) == 1, "compact output should keep skipped items")
    check(len(compact["failed_items"]) == 1, "compact output should keep failed items")
    check("verification_summary" not in compact["ready_items"][0], "compact output should omit verification details")
    check(compact["ready_items"][0]["proposed_field_counts"]["profesionales"] == 1, "compact output should keep useful counts")
    check(
        proposed_field_counts({"profesionales": ["A", "B"], "telefono": "+34", "tech": ""})
        == {"profesionales": 2, "telefono": 1, "tech": 0},
        "proposed field counts should handle lists, scalars and blanks",
    )

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
    check("years_in_practice" in sql, "source batch should include years-in-practice gaps")
    check("specialists_count" in sql, "source batch should include public specialist-count gaps")
    check("team_credentialing_visible" in sql, "source batch should include visible credentialing gaps")
    check("public_pricing" in sql, "source batch should include public-pricing gaps")
    check("prices,public_status" in sql, "source batch should understand nested pricing status")
    check("jsonb_agg(to_jsonb(items) order by items.pending_count desc, items.has_open_review asc, items.team_source_priority desc" in sql, "source batch output should preserve priority order")
    check("cardinality(candidate.pending_fields) desc" in sql, "source batch should prioritize incomplete profiles")
    check("has_open_review asc" in sql, "source batch should prefer sources without open review cards")
    check("source_type" in sql, "source batch should return source type context")
    check("specialists_pending" in sql, "source batch should expose specialist gaps")
    check("team_source_priority" in sql, "source batch should rank team sources")
    check("official_team_page" in sql, "source batch should recognize official team pages")
    check("team_source_priority desc" in sql, "source batch should prefer team pages when specialists are pending")
    team_priority_sql = sql[sql.index("sr.source_type = 'official_team_page'"):sql.index("then 1", sql.index("sr.source_type = 'official_team_page'"))]
    check("medical" not in team_priority_sql.lower(), "source batch should not treat generic medical wording as a team page")
    check("|medic|" not in team_priority_sql.lower(), "source batch should not treat generic medic roots as a team page")
    check("open_review" in sql, "source batch should return existing source review context")
    check("open_clinic_review" in sql, "source batch should return existing clinic review context")
    print("OK source shadow reviews: batch is safe")


if __name__ == "__main__":
    main()
