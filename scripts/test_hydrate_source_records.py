#!/usr/bin/env python3
"""Checks for compact source-record hydration."""

from hydrate_source_records import (
    compact_output,
    fetch_pending_sources,
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
    compact = compact_output({
        "mode": "apply",
        "sources_seen": 2,
        "ready_or_updated": 1,
        "failed": 1,
        "items": [
            {
                "id": "source-1",
                "source_url": "https://clinic.example",
                "status": "updated",
                "updated": {"has_excerpt": True},
                "snapshot": {"content_hash": "hidden"},
            },
            {
                "id": "source-2",
                "source_url": "https://blocked.example",
                "status": "failed",
                "error": "HTTP 403",
            },
        ],
    })
    check(compact["items"][0]["has_excerpt"] is True, "compact output should keep useful flags")
    check("snapshot" not in compact["items"][0], "compact output should omit snapshot details")
    check(compact["items"][1]["error"] == "HTTP 403", "compact output should keep errors")

    captured = {}

    def fake_run_psql(sql, local_env):
        captured["sql"] = sql
        return "[]"

    original_run_psql = fetch_pending_sources.__globals__["run_psql"]
    try:
        fetch_pending_sources.__globals__["run_psql"] = fake_run_psql
        fetch_pending_sources(10, False, False, {})
    finally:
        fetch_pending_sources.__globals__["run_psql"] = original_run_psql

    pending_sql = captured.get("sql", "")
    check("text_sha256' is null" in pending_sql, "pending-source SQL should check text hash")
    check(
        "text_excerpt_empty')::boolean, false) = false" in pending_sql,
        "empty excerpts should not be rehydrated forever",
    )
    print("OK hydrate: source record update")


if __name__ == "__main__":
    main()
