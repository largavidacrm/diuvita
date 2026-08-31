#!/usr/bin/env python3
"""Validate built public clinic pages for Vitalarga profile UX rules."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from validate_data import is_direct_google_maps_profile_url


ROOT = Path(__file__).resolve().parents[1]
CLINIC_DIST = ROOT / "dist" / "clinica"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def link_pairs(source: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for match in re.finditer(r"<a\b[^>]*\bhref=\"([^\"]+)\"[^>]*>(.*?)</a>", source, flags=re.I | re.S):
        href = match.group(1)
        label = re.sub(r"<[^>]+>", " ", match.group(2))
        label = re.sub(r"\s+", " ", label).strip()
        pairs.append((href, label))
    return pairs


def clinic_pages() -> list[Path]:
    if not CLINIC_DIST.exists():
        fail("dist/clinica does not exist; run the static build first")
    return sorted(path for path in CLINIC_DIST.glob("*/index.html") if path.is_file())


def check_location_section(path: Path, source: str) -> None:
    blocks = re.findall(r'<section class="profile-block" id="sedes">([\s\S]*?)</section>', source)
    for block in blocks:
        if re.search(r"<span\b[^>]*>\s*\d+\s*</span>", block):
            fail(f"{path.relative_to(ROOT)}: location section should not show decorative number badges")
        for marker in ("Sede 1", "Sede 2", "Sede 3", "location-index", "section-count", "profile-nav-count"):
            if marker in block:
                fail(f"{path.relative_to(ROOT)}: location section still contains {marker!r}")


def check_google_maps_links(path: Path, source: str) -> None:
    for href, label in link_pairs(source):
        if label.strip().lower() != "google maps":
            continue
        if not is_direct_google_maps_profile_url(href):
            fail(f"{path.relative_to(ROOT)}: Google Maps must open the clinic profile, not a generic address link")


def main() -> None:
    pages = clinic_pages()
    if not pages:
        fail("no built clinic pages found")
    for path in pages:
        source = path.read_text(encoding="utf-8")
        check_location_section(path, source)
        check_google_maps_links(path, source)
    print(f"OK built public profile UX: {len(pages)} clinic pages checked")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
