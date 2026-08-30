#!/usr/bin/env python3
"""Checks that admin evidence cards show rule context for claims."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "admin" / "admin.css").read_text(encoding="utf-8")

    for marker in [
        "function fieldRisk",
        "function ruleDecisionForClaim",
        "LOW_RISK_PREFIXES",
        "MEDIUM_RISK_PREFIXES",
        "HIGH_RISK_PREFIXES",
        "dashboardAutomation = automation",
        "riskPill(decision.risk)",
        "actionPill(decision.action)",
        "function materialChangeItems",
        "Posible impacto",
    ]:
        check(marker in index, f"missing admin claim-rule marker: {marker}")

    for field_path in [
        "units.",
        "professionals.published",
        "team.public_professionals",
    ]:
        check(field_path in index, f"missing medium-risk admin field path: {field_path}")

    check(".claim-main small" in css, "claim reason style missing")
    print("OK admin claim rules: evidence cards show rule context")


if __name__ == "__main__":
    main()
