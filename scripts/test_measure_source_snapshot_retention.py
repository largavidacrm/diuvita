#!/usr/bin/env python3
"""Checks for the read-only source snapshot retention report."""

from measure_source_snapshot_retention import format_retention_report


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    report = {
        "generated_at": "2026-08-30T12:40:00+00:00",
        "summary": {
            "retention_days": 180,
            "keep_latest": 3,
            "total_snapshots": 24,
            "sources_with_snapshots": 15,
            "older_than_retention": 4,
            "protected_latest": 2,
            "prunable_snapshots": 2,
            "oldest_snapshot_at": "2026-01-01T10:00:00+00:00",
            "newest_snapshot_at": "2026-08-30T10:00:00+00:00",
        },
        "top_sources": [
            {
                "clinic_name": "Clinic",
                "clinic_slug": "clinic",
                "source_url": "https://clinic.example/team",
                "snapshots": 5,
                "prunable": 2,
            }
        ],
    }
    output = format_retention_report(report)
    check("# Vitalarga source snapshot retention" in output, "title missing")
    check("Writes data: no" in output, "read-only signal missing")
    check("Keep at least latest snapshots per source: 3" in output, "keep-latest missing")
    check("Consider cleanup only after days: 180" in output, "retention days missing")
    check("Total snapshots: 24" in output, "total snapshots missing")
    check("Cleanup candidates: 2" in output, "cleanup candidates missing")
    check("Clinic | clinic.example/team: 5 snapshots, 2 cleanup candidates" in output, "top source missing")
    one = dict(report)
    one["top_sources"] = [dict(report["top_sources"][0], snapshots=1, prunable=1)]
    one_output = format_retention_report(one)
    check("1 snapshot, 1 cleanup candidate" in one_output, "singular labels missing")
    print("OK retention: source snapshot report")


if __name__ == "__main__":
    main()
