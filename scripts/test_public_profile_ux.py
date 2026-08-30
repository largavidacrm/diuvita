#!/usr/bin/env python3
"""Checks that public clinic pages expose richer profile navigation/search UX."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    for marker in [
        "def profile_nav(",
        "def profile_nav_item(",
        'class="profile-nav"',
        'aria-label="{h(label)}: {h(count)}"',
        'class="profile-nav-count"',
        'id="servicios"',
        'id="unidades"',
        'id="especialistas"',
        '" ".join(c.get("unidades", []))',
        '" ".join(c.get("profesionales", []))',
        'c.get("tech", "")',
    ]:
        check(marker in source, f"missing public profile UX marker: {marker}")

    print("OK public profile UX: navigation and richer search wired")


if __name__ == "__main__":
    main()
