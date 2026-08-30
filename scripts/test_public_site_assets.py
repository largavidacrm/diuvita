#!/usr/bin/env python3
"""Checks that the public site shell has its own basic browser assets."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")

    for marker in [
        'href="/favicon.svg"',
        "FAVICON_SVG",
        'open(os.path.join(DIST, "favicon.svg")',
    ]:
        check(marker in source, f"missing public asset marker: {marker}")

    print("OK public site assets: favicon generated")


if __name__ == "__main__":
    main()
