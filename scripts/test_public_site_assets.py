#!/usr/bin/env python3
"""Checks that the public site shell has its own basic browser assets."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def looks_like_real_logo(path: Path) -> bool:
    head = path.read_bytes()[:512].lstrip().lower()
    if not head:
        return False
    if head.startswith((b"<!doctype", b"<html")) or b"<meta http-equiv" in head[:300]:
        return False
    if path.suffix.lower() == ".svg" and b"<svg" not in head:
        return False
    return True


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    fetch_logos = (ROOT / "scripts" / "fetch_logos.py").read_text(encoding="utf-8")
    logo_status = json.loads((ROOT / "assets" / "logos" / "status.json").read_text(encoding="utf-8"))

    for marker in [
        'href="/favicon.svg"',
        "FAVICON_SVG",
        'open(os.path.join(DIST, "favicon.svg")',
        "def _looks_like_logo_asset",
        "b\"<html\"",
        "_looks_like_logo_asset(os.path.join(dirpath, fn))",
        ".logo-fallback",
        ".logo-failed img{display:none}",
        ".logo-carousel .mini-logo.logo-failed{display:none}",
        "this.closest(\\'.logobox\\').classList.add(\\'logo-failed\\')",
        "this.closest(\\'.mini-logo\\').classList.add(\\'logo-failed\\')",
    ]:
        check(marker in source, f"missing public asset marker: {marker}")

    for marker in [
        "def looks_like_image",
        '"text/html" in lower_ctype',
        'status[slug] = {"ok": False, "error": "descarga no válida: no parece un logo"}',
    ]:
        check(marker in fetch_logos, f"missing logo fetch guard marker: {marker}")

    check(
        not (ROOT / "assets" / "logos" / "thumb" / "tiara-health.svg").exists()
        and not (ROOT / "assets" / "logos" / "orig" / "tiara-health.svg").exists(),
        "Tiara's blocked HTML challenge should not remain as a logo asset",
    )
    check(
        logo_status.get("tiara-health", {}).get("ok") is False
        and "no parece un logo" in logo_status.get("tiara-health", {}).get("error", ""),
        "Tiara logo status should explain the invalid download",
    )

    for logo_dir in [ROOT / "assets" / "logos" / "orig", ROOT / "assets" / "logos" / "thumb"]:
        for path in sorted(logo_dir.iterdir()):
            if path.name == "status.json" or path.name.startswith("."):
                continue
            check(looks_like_real_logo(path), f"invalid logo asset: {path.relative_to(ROOT)}")

    print("OK public site assets: favicon and logo assets guarded")


if __name__ == "__main__":
    main()
