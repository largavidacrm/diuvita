#!/usr/bin/env python3
"""Checks the public-content operational limits scanner."""
from pathlib import Path

from check_operational_limits import ROOT, is_negated_context, scan_text


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    unsafe = "Estas son las mejores clínicas; te conviene hacerte esta prueba porque revierte el envejecimiento."
    strict_unsafe = "Centro clasificado #1 en relación calidad-precio."
    strict_safe_css = ":root{--ink:#17231f;--green:#0E4F4A}"
    safe = (
        "Vitalarga no hace rankings de calidad. Una clínica seria no promete "
        "revertir el envejecimiento ni garantiza resultados milagrosos."
    )

    check(scan_text(ROOT / "data" / "posts" / "unsafe.md", unsafe), "unsafe public claims should be flagged")
    check(
        scan_text(ROOT / "data" / "posts" / "strict.md", strict_unsafe, strict_editorial=True),
        "strict editorial ranking language should be flagged",
    )
    check(
        not scan_text(ROOT / "data" / "posts" / "strict.md", strict_unsafe),
        "strict editorial patterns should stay opt-in",
    )
    check(
        not scan_text(ROOT / "build.py", strict_safe_css, strict_editorial=True),
        "strict editorial ranking should not flag CSS hex colors",
    )
    check(not scan_text(ROOT / "data" / "posts" / "safe.md", safe), "negated safety wording should be allowed")
    check(is_negated_context(safe, safe.index("revertir")), "nearby negation should be detected")
    print("OK operational limits scanner: public red flags detected")


if __name__ == "__main__":
    main()
