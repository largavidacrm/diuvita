#!/usr/bin/env python3
"""Checks for the CTO shadow cycle orchestrator."""
from argparse import Namespace

from run_cto_shadow_cycle import build_steps, compact_summary, try_parse_json


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    check(try_parse_json('{"ok": true}')["ok"] is True, "JSON output should parse")
    check(try_parse_json("plain text") is None, "plain text should not parse")
    check(try_parse_json("") is None, "empty output should be None")
    compact = compact_summary("evaluate_claim_rules", {
        "summary": {"actions": {"review": 2}},
        "evaluations": [{"id": "a"}, {"id": "b"}],
    })
    check(compact["evaluations_count"] == 2, "evaluation count should be kept")
    check("evaluations" not in compact, "full evaluations should be removed")
    compact_items = compact_summary("monitor_source_changes", {
        "changed": 0,
        "items": [
            {
                "source_url": "https://a.test",
                "clinic_name": "A",
                "status": "unchanged",
                "snapshot": {"large": True},
            },
            {
                "source_url": "https://b.test",
                "clinic_name": "B",
                "status": "changed",
                "snapshot": {"large": True},
            },
        ],
    })
    check(compact_items["items_count"] == 2, "items count should be kept")
    check("items" not in compact_items, "full item list should be removed")
    check("snapshot" not in compact_items["sample_items"][0], "large nested snapshot should be omitted")
    compact_top_sources = compact_summary("measure_source_snapshot_retention", {
        "summary": {"total_snapshots": 2},
        "top_sources": [
            {"clinic_name": "A", "source_url": "https://a.test", "snapshots": 3, "prunable": 0, "source_record_id": "large"},
            {"clinic_name": "B", "source_url": "https://b.test", "snapshots": 1, "prunable": 0, "source_record_id": "large"},
        ],
    })
    check(compact_top_sources["top_sources_count"] == 2, "top source count should be kept")
    check("top_sources" not in compact_top_sources, "full top source list should be removed")
    check("source_url" in compact_top_sources["sample_top_sources"][0], "source url should distinguish compact top sources")
    check("source_record_id" not in compact_top_sources["sample_top_sources"][0], "large source ids should be omitted")
    compact_source_shadow = compact_summary("submit_source_shadow_reviews", {
        "items": [
            {
                "clinic_slug": "example",
                "clinic_name": "Example",
                "source_url": "https://example.test",
                "status": "ready",
                "proposed_fields": ["email"],
                "verification_summary": {"large": True},
            }
        ],
    })
    check(compact_source_shadow["items_count"] == 1, "source shadow count should be kept")
    check("verification_summary" not in compact_source_shadow["sample_items"][0], "large source shadow details should be omitted")
    steps = build_steps(Namespace(
        apply_safe=False,
        review_limit=2,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=0,
        source_shadow_clinic_slug=None,
        source_shadow_replace_existing=False,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        fetch_timeout=7,
    ))
    names = [step[0] for step in steps]
    check("process_source_change_reviews" in names, "source-change processing step missing")
    check("submit_source_shadow_reviews" not in names, "source shadow batch should be off by default")
    check("submit_blocking_claim_reviews" in names, "blocking-claim review step missing")
    check("measure_source_snapshot_retention" in names, "source snapshot retention step missing")
    check("evaluate_claim_rules" in names, "claim rule evaluation step missing")
    source_change_step = [step for step in steps if step[0] == "process_source_change_reviews"][0]
    check("8" in source_change_step[1], "source-change limit should be passed through")
    blocking_step = [step for step in steps if step[0] == "submit_blocking_claim_reviews"][0]
    check("9" in blocking_step[1], "blocking-claim limit should be passed through")
    retention_step = [step for step in steps if step[0] == "measure_source_snapshot_retention"][0]
    check("--json" in retention_step[1], "retention report should be machine readable")
    check("180" in retention_step[1] and "3" in retention_step[1] and "7" in retention_step[1], "retention settings should pass through")
    claim_step = [step for step in steps if step[0] == "evaluate_claim_rules"][0]
    check("--json" in claim_step[1], "claim rule evaluation should be machine readable")
    check("6" in claim_step[1], "claim limit should be passed through")
    optional_steps = build_steps(Namespace(
        apply_safe=True,
        review_limit=2,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=2,
        source_shadow_clinic_slug="sensabell",
        source_shadow_replace_existing=True,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        fetch_timeout=7,
    ))
    source_shadow_step = [step for step in optional_steps if step[0] == "submit_source_shadow_reviews"][0]
    check("--apply" in source_shadow_step[1], "source shadow batch should follow safe apply mode")
    check("--clinic-slug" in source_shadow_step[1] and "sensabell" in source_shadow_step[1], "source shadow clinic slug should pass through")
    check("--replace-existing" in source_shadow_step[1], "source shadow replace flag should pass through")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
