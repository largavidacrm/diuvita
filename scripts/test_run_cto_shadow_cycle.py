#!/usr/bin/env python3
"""Checks for the CTO shadow cycle orchestrator."""

from run_cto_shadow_cycle import try_parse_json


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    check(try_parse_json('{"ok": true}')["ok"] is True, "JSON output should parse")
    check(try_parse_json("plain text") is None, "plain text should not parse")
    check(try_parse_json("") is None, "empty output should be None")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
