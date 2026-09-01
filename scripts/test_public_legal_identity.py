#!/usr/bin/env python3
"""Checks that the public site exposes the approved legal identity."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    limits = (ROOT / "docs" / "VITALARGA_LIMITES_OPERATIVOS.md").read_text(encoding="utf-8")

    for marker in [
        "LEGAL_OWNER",
        "Neurotrans SLU",
        "B-67221093",
        "Padilla 327 Ent 68",
        "08025 Barcelona",
        "admin@neurotrans.es",
        "aviso-legal",
        "privacidad",
        "cookies",
        "legal_owner_summary_html",
        "legal_owner_block",
    ]:
        check(marker in source, f"missing public legal marker: {marker}")

    footer_start = source.index("FOOTER =")
    footer_end = source.index("def attrs", footer_start)
    footer_source = source[footer_start:footer_end]
    check("legal_owner_summary_html()" not in footer_source, "footer should not expose the full legal owner")
    check("Titular:" not in footer_source, "footer should not show the legal-owner label")

    for marker in [
        "Titular legal",
        "Neurotrans SLU",
        "B-67221093",
        "Padilla 327 Ent 68, 08025 Barcelona",
        "admin@neurotrans.es",
    ]:
        check(marker in limits, f"missing legal limits marker: {marker}")

    print("OK public legal identity: approved owner details wired")


if __name__ == "__main__":
    main()
