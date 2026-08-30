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
        ".profile-sections{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:1.5rem;align-items:start}",
        ".profile-block{min-width:0;padding:1.05rem 1.1rem;border:1px solid var(--line);border-radius:8px;background:var(--surface);box-shadow:0 1px 0 rgba(23,35,31,.03)}",
        ".clinic-side .profile-block{margin-top:0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none}",
        ".profile-block li{margin:.24rem 0}",
        '" ".join(c.get("unidades", []))',
        '" ".join(c.get("profesionales", []))',
        'c.get("tech", "")',
    ]:
        check(marker in source, f"missing public profile UX marker: {marker}")

    print("OK public profile UX: navigation and richer search wired")


if __name__ == "__main__":
    main()
