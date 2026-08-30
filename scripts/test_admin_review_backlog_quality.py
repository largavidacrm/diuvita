#!/usr/bin/env python3
"""Checks that the admin dashboard shows repeated enrichment-card pressure."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function reviewBacklogQuality",
        "duplicateClinics",
        "duplicateReviews",
        "Duplicados mejoras",
        "Tarjetas duplicadas",
        "Sin duplicados",
    ]:
        check(marker in index, f"missing admin review backlog marker: {marker}")

    print("OK admin review backlog: duplicate pressure visible")


if __name__ == "__main__":
    main()
