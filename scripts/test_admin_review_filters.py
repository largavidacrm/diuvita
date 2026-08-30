#!/usr/bin/env python3
"""Checks that the admin review inbox quick filters are wired."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        'id="reviewFilterChips"',
        'id="reviewClearFilters"',
        "REVIEW_TYPE_FILTERS",
        "REVIEW_PRIORITY_FILTERS",
        "function renderReviewFilterChips",
        "function reviewMatchesType",
        "function clearReviewFilters",
        'value="blocking_claim_review"',
        '["blocking_claim_review", "Claims bloqueantes"]',
        "data-review-type",
        "data-review-priority",
        "data-review-duplicate",
        "reviewDuplicateFilter",
    ]:
        check(marker in index, f"missing admin review filter marker: {marker}")

    for marker in [
        ".review-filter-panel",
        ".filter-chip-row",
        ".filter-chip",
        ".filter-chip.active",
    ]:
        check(marker in css, f"missing admin review filter style: {marker}")

    check(
        'el("reviewFilterChips").addEventListener("click"' in index,
        "quick filter clicks should be handled",
    )
    print("OK admin review filters: controls wired")


if __name__ == "__main__":
    main()
