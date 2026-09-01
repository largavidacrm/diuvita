#!/usr/bin/env python3
"""Checks that the public home keeps useful filters without the old stats strip."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    check("hero-stats" not in source, "home should not render the removed stats strip")

    check('<input id="q" type="search"' in source, "home search input should remain")
    check("filter-grid" in source, "home filters should remain")
    check("country_chips" in source, "country chips should remain")
    check("city_chips" in source, "city chips should remain")
    check("spec_chips" in source, "specialty chips should remain")
    check("logo-carousel" in source, "home logo area should be a carousel")
    check("data-logo-carousel" in source, "home logo carousel should have a behavior hook")
    check("logo-viewport" in source, "home logo carousel should have a clipped viewport")
    check("function ensureLoop" in source, "home logo carousel should loop instead of ending at the last logo")
    check("logo-clone" in source, "home logo carousel should duplicate logos internally for continuous movement")
    check('clone.setAttribute("aria-hidden","true")' in source, "home logo carousel clones should stay out of accessibility navigation")
    check('data-logo-nav="prev"' in source, "home logo carousel should have previous control")
    check('data-logo-nav="next"' in source, "home logo carousel should have next control")
    check("setupLogoCarousel" in source, "home logo carousel should initialize")
    check("logo-strip" in source, "home logo strip should remain")
    check("mini-logo" in source, "home logo links should remain")
    check('class="mini-logo" href="/clinica/{h(c["slug"])}/"' in source, "home logo strip should link to clinic profiles")
    check('class="results-section"' in source, "clinic results should remain")
    check("def card_logo(" in source, "clinic card logos should have a dedicated link helper")
    check('class="logo-link"' in source, "clinic card logos should be clickable")
    check('aria-label="Ver ficha de {h(c["name"])}"' in source, "logo links should be accessible")
    print("OK public home: useful filters and logos preserved")


if __name__ == "__main__":
    main()
