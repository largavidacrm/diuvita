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
    logo_config = json.loads((ROOT / "data" / "logos.json").read_text(encoding="utf-8"))
    logo_status = json.loads((ROOT / "assets" / "logos" / "status.json").read_text(encoding="utf-8"))

    for marker in [
        'href="/favicon.svg"',
        "FAVICON_SVG",
        'open(os.path.join(DIST, "favicon.svg")',
        "def _looks_like_logo_asset",
        "LOGO_STATUS_FILE",
        '_logo_status[_slug].get("ok") is False',
        "b\"<html\"",
        "_looks_like_logo_asset(os.path.join(dirpath, fn))",
        ".logo-fallback",
        ".logo-failed img{display:none}",
        ".logo-carousel .mini-logo.logo-failed{display:none}",
        "function removeFailedCarouselLogo",
        "function bindLogoImageGuards",
        "img.naturalWidth===0||img.naturalHeight===0",
        'candidate.getAttribute("data-slug")===slug',
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
        logo_config.get("tiara-health", {}).get("aprobado") is False,
        "Tiara's invalid source should not stay approved as a logo",
    )
    check(
        logo_status.get("tiara-health", {}).get("ok") is False
        and (
            "no parece un logo" in logo_status.get("tiara-health", {}).get("error", "")
            or logo_status.get("tiara-health", {}).get("skipped") == "no aprobado"
        ),
        "Tiara logo status should explain why it is not active",
    )

    for logo_dir in [ROOT / "assets" / "logos" / "orig", ROOT / "assets" / "logos" / "thumb"]:
        for path in sorted(logo_dir.iterdir()):
            if path.name == "status.json" or path.name.startswith("."):
                continue
            check(looks_like_real_logo(path), f"invalid logo asset: {path.relative_to(ROOT)}")

    print("OK public site assets: favicon and logo assets guarded")


if __name__ == "__main__":
    main()
