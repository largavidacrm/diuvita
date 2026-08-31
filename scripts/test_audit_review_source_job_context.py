#!/usr/bin/env python3
"""Checks for source-job context audits on review cards."""

from audit_review_source_job_context import audit_row, format_report, summarize


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    ready = audit_row({
        "id": "review-ready",
        "title": "Revisar extracción shadow: IMDA",
        "clinic_name": "IMDA",
        "payload": {
            "source_url": "https://imda.example/contacto",
            "human_supplied_source": True,
            "target_scope": "primary_target_first",
            "requested_fields": ["profesionales"],
        },
    })
    recoverable = audit_row({
        "id": "review-recoverable",
        "title": "Revisar extracción shadow: Tiara Health",
        "clinic_name": "Tiara Health",
        "payload": {
            "job_id": "job-tiara",
            "source_url": "https://www.tiarahealth.com/our-team-of-experts/",
        },
        "job_input": {
            "human_supplied_source": True,
            "from_review_id": "quality-tiara",
            "target_scope": "primary_target_first",
            "primary_requested_fields": ["profesionales"],
            "allowed_output": "review_queue_proposal_only",
        },
    })
    missing = audit_row({
        "id": "review-missing",
        "title": "Revisar extracción shadow: Example",
        "clinic_name": "Example Clinic",
        "payload": {"source_url": "https://example.test/team"},
    })

    check(ready["status"] == "context_ready", "ready payload context should be detected")
    check(ready["source_host"] == "imda.example", "ready source host missing")
    check(recoverable["status"] == "recoverable_from_job", "recoverable job context should be detected")
    check(recoverable["job_context"]["primary_requested_fields"] == ["profesionales"], "job primary field missing")
    check(missing["status"] == "source_without_context", "source without context should be flagged")

    summary = summarize([ready, recoverable, missing])
    check(summary["cards"] == 3, "summary card count missing")
    check(summary["context_ready"] == 1, "ready count missing")
    check(summary["recoverable_from_job"] == 1, "recoverable count missing")
    check(summary["source_without_context"] == 1, "missing-context count missing")

    output = format_report({
        "generated_at": "2026-08-31T22:09:00+00:00",
        "query": "Tiara",
        "summary": summary,
        "items": [ready, recoverable, missing],
    }, compact=True)
    check("Writes data: no" in output, "report should be read-only")
    check("Tiara Health: recoverable_from_job" in output, "report should show recoverable Tiara row")
    check("https://www.tiarahealth.com/our-team-of-experts/" not in output, "compact report should hide full URLs")
    print("OK review source-job context audit: missing context is visible")


if __name__ == "__main__":
    main()
