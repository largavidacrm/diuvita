#!/usr/bin/env python3
"""Checks that the public home stays simple on mobile."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    for removed in [
        "hero-stats",
        "logo-strip",
        "mini-logo",
        "filter-grid",
        "fgroup",
        "country_chips",
        "city_chips",
        "spec_chips",
    ]:
        check(removed not in source, f"home should not render removed mobile clutter: {removed}")

    check('<input id="q" type="search"' in source, "home search input should remain")
    check('class="results-section"' in source, "clinic results should remain")
    check("def card_logo(" in source, "clinic card logos should have a dedicated link helper")
    check('class="logo-link"' in source, "clinic card logos should be clickable")
    check('aria-label="Ver ficha de {h(c["name"])}"' in source, "logo links should be accessible")
    print("OK public home: simplified mobile layout")


if __name__ == "__main__":
    main()
