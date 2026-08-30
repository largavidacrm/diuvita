#!/usr/bin/env python3
"""Checks for safe batch shadow reviews from existing clinic sources."""
from argparse import Namespace

from capture_source_snapshot import FetchResult
from submit_source_shadow_reviews import process_source, summarize_results


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
        "has_open_review": False,
    }
    args = Namespace(timeout=15, apply=False, replace_existing=False)
    result = process_source(source, args, "admin@example.test", {}, fetcher=fake_fetch)
    check(result["status"] == "ready", "source should produce a ready review payload")
    check("email" in result["proposed_fields"], "email proposal missing")
    check("profesionales" in result["proposed_fields"], "professional proposal missing")

    skipped = process_source(
        dict(source, has_open_review=True),
        args,
        "admin@example.test",
        {},
        fetcher=fake_fetch,
    )
    check(skipped["status"] == "skipped", "existing open review should be skipped by default")
    check("already exists" in skipped["reason"], "skip reason should be readable")

    calls = []

    def fake_create_review(clinic_slug, payload, admin_email, local_env, replace_existing):
        calls.append((clinic_slug, payload, admin_email, replace_existing))
        return {"status": "inserted", "id": "review-1"}

    apply_args = Namespace(timeout=15, apply=True, replace_existing=True)
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

    summary = summarize_results([result, skipped, applied])
    check(summary["sources_seen"] == 3, "summary source count missing")
    check(summary["ready"] == 2, "summary ready count missing")
    check(summary["skipped"] == 1, "summary skipped count missing")
    check(summary["created_or_updated"] == 1, "summary created count missing")
    print("OK source shadow reviews: batch is safe")


if __name__ == "__main__":
    main()
