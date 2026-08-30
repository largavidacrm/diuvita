#!/usr/bin/env python3
"""Basic checks for compact source snapshots."""
from capture_source_snapshot import (
    FetchResult,
    safe_host,
    snapshot_from_fetch,
    snapshot_path,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    body = b"""
<!doctype html>
<html>
<head><title>Example Longevity Clinic</title><style>.x{}</style></head>
<body>
  <h1>Example Clinic</h1>
  <script>window.secret = "ignore";</script>
  <p>Longevity diagnostics and VO2 max testing.</p>
</body>
</html>
"""
    snapshot = snapshot_from_fetch(
        FetchResult(
            source_url="https://clinic.example/longevity",
            final_url="https://clinic.example/longevity",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=body,
        )
    )
    check(snapshot["source_title"] == "Example Longevity Clinic", "title extraction failed")
    check("VO2 max" in snapshot["text_excerpt"], "readable text missing")
    check("window.secret" not in snapshot["text_excerpt"], "script text should be ignored")
    check(len(snapshot["content_sha256"]) == 64, "hash should be sha256")
    check(safe_host("https://Clinic.Example/a") == "clinic.example", "host normalization failed")
    path = snapshot_path(snapshot)
    check(str(path).endswith(".json"), "snapshot path should be json")
    print("OK snapshots: compact source capture")


if __name__ == "__main__":
    main()
