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
    steps = build_steps(Namespace(
        apply_safe=False,
        review_limit=2,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        fetch_timeout=7,
    ))
    names = [step[0] for step in steps]
    check("process_source_change_reviews" in names, "source-change processing step missing")
    check("submit_blocking_claim_reviews" in names, "blocking-claim review step missing")
    check("evaluate_claim_rules" in names, "claim rule evaluation step missing")
    source_change_step = [step for step in steps if step[0] == "process_source_change_reviews"][0]
    check("8" in source_change_step[1], "source-change limit should be passed through")
    blocking_step = [step for step in steps if step[0] == "submit_blocking_claim_reviews"][0]
    check("9" in blocking_step[1], "blocking-claim limit should be passed through")
    claim_step = [step for step in steps if step[0] == "evaluate_claim_rules"][0]
    check("--json" in claim_step[1], "claim rule evaluation should be machine readable")
    check("6" in claim_step[1], "claim limit should be passed through")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
