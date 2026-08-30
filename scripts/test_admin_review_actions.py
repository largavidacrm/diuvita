#!/usr/bin/env python3
"""Checks that admin review actions keep their context after closing panels."""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    match = re.search(r"async function dismissReview\(\) \{([\s\S]+?)\n    \}", index)
    check(match is not None, "dismissReview function missing")
    body = match.group(1)

    check(
        "var reviewType = activeReview.review_type;" in body,
        "dismissReview should keep review type before closing",
    )
    check(
        'var note = trimmed("reviewResolutionNote") || defaultDismissNote(reviewType);' in body,
        "dismissReview should keep the resolution note before closing",
    )
    check("p_note: note" in body, "dismissReview should submit the preserved note")

    after_close = body.split("closeReviewEditor();", 1)[-1]
    check(
        "activeReview.review_type" not in after_close,
        "dismissReview should not read activeReview after closeReviewEditor",
    )
    print("OK admin review actions: dismiss keeps context")


if __name__ == "__main__":
    main()
