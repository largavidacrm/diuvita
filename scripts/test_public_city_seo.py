#!/usr/bin/env python3
"""Checks for the first controlled city SEO landing layer."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    for marker in [
        'PRIORITY_SEO_CITIES = ("Barcelona", "Madrid", "Marbella", "Valencia")',
        "def city_intro(",
        "def city_checklist(",
        "def city_jsonld(",
        "def city_seo_blocks(",
        "CollectionPage",
        "ItemList",
        "itemListOrder",
        "https://schema.org/Unordered",
        "city-links",
        "city-link-row",
        "Páginas principales por ciudad",
        "Qué comparar antes de contactar",
        "Orden rotatorio neutral: no representa recomendación ni valoración médica.",
        "la presencia de una clínica no equivale a aval médico",
    ]:
        check(marker in source, f"missing city SEO marker: {marker}")

    for city in ("Barcelona", "Madrid", "Marbella", "Valencia"):
        check(f'Clínicas de longevidad en {{h(city)}}' in source or city in source, f"{city} should be part of the priority city layer")

    for risky in [
        "mejores clínicas de longevidad en",
        "top clínicas",
        "ranking de clínicas",
        "recomendamos estas clínicas",
    ]:
        check(risky not in source.lower(), f"city SEO should not use ranking/recommendation wording: {risky}")

    print("OK public city SEO: controlled city landing layer")


if __name__ == "__main__":
    main()
