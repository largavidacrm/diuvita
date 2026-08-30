#!/usr/bin/env python3
"""Checks for compact source-record hydration."""

from hydrate_source_records import (
    first_json_line,
    record_failure_sql,
    snapshot_metadata,
    update_source_record_sql,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    snapshot = {
        "source_title": "Clinic page",
        "retrieved_at": "2026-08-30T09:00:00Z",
        "final_url": "https://clinic.example/final",
        "http_status": 200,
        "content_type": "text/html; charset=utf-8",
        "request_profile": "browser_compatible",
        "content_sha256": "abc123",
        "text_sha256": "def456",
        "content_length": 1234,
        "text_excerpt": "Readable clinic text",
    }
    metadata = snapshot_metadata(snapshot)
    sql = update_source_record_sql("00000000-0000-0000-0000-000000000001", snapshot)
    check(metadata["hydrated_by"] == "vitalarga-source-hydrator", "hydrator metadata missing")
    check(metadata["final_url"] == "https://clinic.example/final", "final URL missing")
    check(metadata["request_profile"] == "browser_compatible", "request profile missing")
    check(metadata["text_sha256"] == "def456", "text hash metadata missing")
    check(metadata["text_excerpt_empty"] is False, "excerpt flag should be false")
    check("content_hash = 'abc123'" in sql, "content hash update missing")
    check("raw_excerpt = 'Readable clinic text'" in sql, "excerpt update missing")
    failure_sql = record_failure_sql("00000000-0000-0000-0000-000000000001", "https://clinic.example", "HTTP 403")
    check("last_hydration_error" in failure_sql, "failure metadata missing")
    parsed = first_json_line('{"ok": true}\nUPDATE 1')
    check(parsed["ok"] is True, "psql JSON line parsing failed")
    print("OK hydrate: source record update")


if __name__ == "__main__":
    main()
