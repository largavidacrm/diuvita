#!/usr/bin/env python3
"""Checks that public clinic lists use a neutral rotating order."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    for marker in [
        "ORDER_NOTE",
        "El orden de las fichas rota de forma neutra",
        "no es un ranking ni una recomendación médica",
        "NEUTRAL_ORDER_JS",
        "function hashText",
        "function daySeed",
        "Date.UTC",
        "function neutralOrderKey",
        "window.applyNeutralCardOrder",
        "data-neutral-results=\"home-clinics\"",
        "data-neutral-results=\"home-logos\"",
        "data-neutral-results=\"city:{h(city)}\"",
        "data-neutral-item",
        "data-slug=\"{h(c[\"slug\"])}\"",
        "featured_logo_clinics = [c for c in clinics if c.get(\"slug\") in thumb_files]",
    ]:
        check(marker in source, f"missing neutral order marker: {marker}")

    check("Math.random" not in source, "public order should be stable for the day, not random on every reload")
    check(
        "featured_logo_clinics = [c for c in clinics if c.get(\"slug\") in thumb_files][:12]" not in source,
        "logo carousel should not keep an arbitrary first-12 shortlist",
    )
    check(
        '<div class="grid">{allcards}</div>' not in source,
        "home clinic grid should be marked for neutral ordering",
    )

    print("OK public neutral order: cards and logos rotate without ranking")


if __name__ == "__main__":
    main()
