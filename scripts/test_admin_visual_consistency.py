#!/usr/bin/env python3
"""Checks that the admin dashboard keeps a compact, consistent visual scale."""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for token in [
        "--text-label",
        "--text-small",
        "--text-ui",
        "--text-body",
        "--text-title-sm",
        "--text-title-md",
        "--text-title-lg",
        "--text-stat",
    ]:
        check(token in css, f"missing dashboard typography token: {token}")

    check("letter-spacing: -" not in css, "dashboard should not use negative letter spacing")
    check(".work-grid.review-work-queue" in css, "review queue layout mode missing")
    check(".work-grid.review-work-decision" in css, "review decision layout mode missing")
    check(
        "minmax(0, 1fr) minmax(260px, 320px)" in css
        and "minmax(0, 0.95fr) minmax(400px, 1.05fr)" in css,
        "review workspace should keep stable desktop columns",
    )

    review_queue = css[css.index(".review-subject-cell {"):css.index(".empty {")]
    for marker in [
        ".review-table th:nth-child(1)",
        "width: 40%;",
        ".review-table th:nth-child(2)",
        "width: 20%;",
        ".review-table th:nth-child(3)",
        "width: 16%;",
        "-webkit-line-clamp: 2;",
        "font-size: var(--text-ui);",
        "vertical-align: top;",
    ]:
        check(marker in review_queue, f"review table should stay compact and predictable: {marker}")

    normal_pixel_radii = [
        int(match.group(1))
        for match in re.finditer(r"border-radius:\s*(\d+)px", css)
        if int(match.group(1)) < 90
    ]
    check(normal_pixel_radii, "expected explicit pixel radii")
    check(max(normal_pixel_radii) <= 8, "dashboard cards and controls should stay at 8px radius or less")
    check("border-radius: 99px;" in css or "border-radius: 999px;" in css, "rounded pills should stay explicit")

    review_raw_sizes = [
        value
        for value in re.findall(r"font-size:\s*([0-9]+(?:\.[0-9]+)?)rem", review_queue)
        if float(value) > 1.05
    ]
    check(
        not review_raw_sizes,
        "review queue should not use raw large font sizes; use compact tokens instead",
    )

    print("OK admin visual consistency: dashboard scale is compact")


if __name__ == "__main__":
    main()
