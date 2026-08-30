#!/usr/bin/env python3
"""Checks for durable compact source snapshot SQL helpers."""

from source_snapshot_records import insert_source_snapshot_sql, snapshot_metadata, snapshot_storage_path


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    snapshot = {
        "source_url": "https://clinic.example/source",
        "final_url": "https://clinic.example/final",
        "source_title": "Clinic",
        "retrieved_at": "2026-08-30T09:00:00Z",
        "http_status": 200,
        "content_type": "text/html",
        "content_length": 123,
        "content_sha256": "abc123",
        "text_sha256": "def456",
        "text_excerpt": "Readable clinic text",
    }
    path = snapshot_storage_path(snapshot)
    metadata = snapshot_metadata(snapshot, "tester", "1.0", {"changed": False})
    sql = insert_source_snapshot_sql(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "clinic_id": "00000000-0000-0000-0000-000000000002",
            "entity_type": "clinic",
        },
        snapshot,
        "tester",
        "1.0",
        {"changed": False},
    )
    check(path == "source_snapshots/2026/08/clinic.example/abc123.json", "snapshot path mismatch")
    check(metadata["observed_by"] == "tester", "observer missing")
    check(metadata["changed"] is False, "extra metadata missing")
    check("insert into public.source_snapshots" in sql, "insert missing")
    check("on conflict" in sql, "idempotent upsert missing")
    check("Readable clinic text" in sql, "excerpt missing")
    print("OK snapshots: durable source rows")


if __name__ == "__main__":
    main()
