#!/usr/bin/env python3
"""Checks for the CTO shadow cycle orchestrator."""
from argparse import Namespace

from run_cto_shadow_cycle import build_steps, try_parse_json


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    check(try_parse_json('{"ok": true}')["ok"] is True, "JSON output should parse")
    check(try_parse_json("plain text") is None, "plain text should not parse")
    check(try_parse_json("") is None, "empty output should be None")
    steps = build_steps(Namespace(
        apply_safe=False,
        review_limit=2,
        source_limit=3,
        monitor_limit=4,
        digest_limit=5,
        claim_limit=6,
        fetch_timeout=7,
    ))
    names = [step[0] for step in steps]
    check("evaluate_claim_rules" in names, "claim rule evaluation step missing")
    claim_step = [step for step in steps if step[0] == "evaluate_claim_rules"][0]
    check("--json" in claim_step[1], "claim rule evaluation should be machine readable")
    check("6" in claim_step[1], "claim limit should be passed through")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
