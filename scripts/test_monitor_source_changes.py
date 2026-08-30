#!/usr/bin/env python3
"""Checks for source change monitoring."""

from monitor_source_changes import compare_record, create_review_sql, first_json_line


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    record = {
        "id": "source-1",
        "clinic_id": "00000000-0000-0000-0000-000000000001",
        "clinic_slug": "clinic",
        "clinic_name": "Clinic",
        "source_url": "https://clinic.example",
        "content_hash": "old",
        "metadata": {"text_sha256": "old-text"},
        "retrieved_at": "2026-08-30T09:00:00Z",
    }
    snapshot = {
        "content_sha256": "new",
        "text_sha256": "new-text",
        "retrieved_at": "2026-08-30T10:00:00Z",
        "source_title": "Clinic title",
        "text_excerpt": "New text",
    }
    change = compare_record(record, snapshot)
    check(change["changed"] is True, "hash change not detected")
    check(change["hash_type"] == "text", "text hash should be preferred")
    sql = create_review_sql(change, "admin@example.com")
    check("source_change_detected" in sql, "review type missing")
    check("previous_hash" in sql and "current_hash" in sql, "hash evidence missing")
    parsed = first_json_line('NOTICE\n{"status": "inserted"}')
    check(parsed["status"] == "inserted", "JSON parser failed")
    print("OK monitor: source change detection")


if __name__ == "__main__":
    main()
