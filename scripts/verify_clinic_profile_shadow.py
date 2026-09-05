#!/usr/bin/env python3
"""Independent shadow verifier for extracted clinic profile claims."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from capture_source_snapshot import normalize_space
from vitalarga_rules import decide_many

TEAM_CREDENTIALING_SIGNAL_RE = re.compile(
    r"\b(?:n[ºo]\s*colegiad[oa]|n[uú]mero\s+de\s+colegiad[oa]|"
    r"colegiad[oa]\s*(?:n[ºo]|n[uú]mero)|col\.)\b",
    re.I,
)
PUBLIC_PRICING_SIGNAL_RE = re.compile(
    r"(?:precio|tarifa|consulta|programa|bono)[^.]{0,90}(?:€|eur|euros)|"
    r"(?:€|eur|euros)[^.]{0,90}(?:precio|tarifa|consulta|programa|bono)",
    re.I,
)
CLINIC_REGISTRY_SIGNAL_RE = re.compile(
    r"\b(?:registro\s+sanitario|regcess|n[uú]mero\s+de\s+registro|centro\s+sanitario)\b",
    re.I,
)
PROFESSIONAL_LICENSE_SIGNAL_RE = re.compile(
    r"\b(?:n[ºo]\s*colegiad[oa]|n[uú]mero\s+de\s+colegiad[oa]|colegiad[oa]\s*(?:n[ºo]|n[uú]mero)|col\.)\b",
    re.I,
)


def normalized_text(value: Any) -> str:
    return normalize_space(str(value or "")).lower()


def digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def host(value: Any) -> str:
    parsed = urlparse(str(value or ""))
    return parsed.netloc.lower().removeprefix("www.")


def source_text(extraction: dict[str, Any]) -> str:
    source = extraction.get("source") or {}
    return normalized_text(
        " ".join([
            str(source.get("source_title") or ""),
            str(source.get("text_excerpt") or ""),
        ])
    )


def source_host(extraction: dict[str, Any]) -> str:
    source = extraction.get("source") or {}
    return host(source.get("final_url") or source.get("source_url") or "")


def value_supported(value: Any, haystack: str) -> tuple[bool, str]:
    if isinstance(value, list):
        values = [normalized_text(item) for item in value if normalized_text(item)]
        if not values:
            return False, "empty list"
        supported = [item for item in values if item in haystack]
        if len(supported) == len(values):
            return True, "all values found explicitly"
        if supported:
            return False, f"partial support: {len(supported)} of {len(values)} values"
        return False, "values not found explicitly"

    clean = normalized_text(value)
    if not clean:
        return False, "empty value"
    if clean in haystack:
        return True, "value found explicitly"
    return False, "value not found explicitly"


def verify_locations(value: Any, haystack: str) -> tuple[str, float, str]:
    if not isinstance(value, list):
        return "review", 0.50, "location value is not a list"
    addresses = []
    for item in value:
        if isinstance(item, dict):
            address = normalized_text(item.get("address") or item.get("direccion") or item.get("dirección"))
        else:
            address = normalized_text(item)
        if address:
            addresses.append(address)
    if not addresses:
        return "review", 0.50, "empty location list"
    supported = [address for address in addresses if address in haystack]
    if len(supported) == len(addresses):
        return "accepted", 0.90, "all location addresses found explicitly"
    if supported:
        return "review", 0.72, f"partial location support: {len(supported)} of {len(addresses)} addresses"
    return "review", 0.60, "location addresses need manual review"


def verify_contact_phone(value: Any, haystack: str) -> tuple[str, float, str]:
    claim_digits = digits(value)
    if len(claim_digits) < 7:
        return "review", 0.40, "phone value is too short"
    text_digits = digits(haystack)
    if claim_digits in text_digits:
        return "accepted", 0.94, "phone digits found explicitly"
    return "rejected", 0.88, "phone digits not found"


def verify_digit_value(value: Any, haystack: str, signal_re: re.Pattern[str], label: str) -> tuple[str, float, str]:
    values = value if isinstance(value, list) else [value]
    value_digits = [digits(item) for item in values if digits(item)]
    if not value_digits:
        return "review", 0.50, f"{label} value is empty"
    text_digits = digits(haystack)
    supported = [item for item in value_digits if item in text_digits]
    if len(supported) == len(value_digits) and signal_re.search(haystack):
        return "accepted", 0.82, f"{label} digits and label found explicitly"
    if supported:
        return "review", 0.68, f"{label} digits found but need manual confirmation"
    return "review", 0.60, f"{label} needs manual review"


def verify_price_value(value: Any, haystack: str) -> tuple[str, float, str]:
    value_digits = digits(value)
    if not value_digits:
        return "review", 0.50, "price value is empty"
    if value_digits in digits(haystack) and PUBLIC_PRICING_SIGNAL_RE.search(haystack):
        return "accepted", 0.82, "price amount and pricing signal found explicitly"
    return "review", 0.62, "price needs manual review"


def verify_claim(claim: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    field_path = str(claim.get("field_path") or "")
    value = claim.get("value")
    haystack = source_text(extraction)
    clean_source_host = source_host(extraction)

    verdict = "review"
    confidence = 0.50
    reason = "no verifier rule matched"

    if field_path == "contact.website":
        if host(value) and host(value) == clean_source_host:
            verdict, confidence, reason = "accepted", 0.96, "website host matches source host"
        else:
            verdict, confidence, reason = "review", 0.65, "website host does not match source host"
    elif field_path.startswith("contact.phone"):
        verdict, confidence, reason = verify_contact_phone(value, haystack)
    elif field_path.startswith("contact."):
        supported, reason = value_supported(value, haystack)
        verdict = "accepted" if supported else "rejected"
        confidence = 0.94 if supported else 0.86
    elif field_path.startswith("identity."):
        supported, reason = value_supported(value, haystack)
        verdict = "accepted" if supported else "review"
        confidence = 0.66 if supported else 0.45
    elif field_path.startswith("profile."):
        supported, reason = value_supported(value, haystack)
        verdict = "accepted" if supported else "review"
        confidence = 0.88 if supported else 0.58
    elif field_path.startswith("location."):
        verdict, confidence, reason = verify_locations(value, haystack)
    elif field_path.startswith(("services.", "specialties.", "units.", "diagnostics.", "programs.", "technologies.", "professionals.")):
        supported, reason = value_supported(value, haystack)
        verdict = "accepted" if supported else "review"
        confidence = 0.90 if supported else 0.62
    elif field_path.startswith("transparency."):
        supported, reason = value_supported(value, haystack)
        verdict = "accepted" if supported else "review"
        confidence = 0.90 if supported else 0.62
    elif field_path.startswith("clinic.registry"):
        verdict, confidence, reason = verify_digit_value(
            value,
            haystack,
            CLINIC_REGISTRY_SIGNAL_RE,
            "clinic registry",
        )
    elif field_path == "team.professional_license_numbers":
        verdict, confidence, reason = verify_digit_value(
            value,
            haystack,
            PROFESSIONAL_LICENSE_SIGNAL_RE,
            "professional license",
        )
    elif field_path == "team.credentialing_visible":
        if TEAM_CREDENTIALING_SIGNAL_RE.search(haystack):
            verdict, confidence, reason = "accepted", 0.88, "professional credentialing signal found explicitly"
        else:
            verdict, confidence, reason = "review", 0.58, "credentialing signal needs manual review"
    elif field_path == "prices.public_status":
        if PUBLIC_PRICING_SIGNAL_RE.search(haystack):
            verdict, confidence, reason = "accepted", 0.88, "public pricing signal found explicitly"
        else:
            verdict, confidence, reason = "review", 0.58, "pricing signal needs manual review"
    elif field_path == "prices.initial_visit":
        verdict, confidence, reason = verify_price_value(value, haystack)
    elif field_path == "prices.url":
        source = extraction.get("source") or {}
        source_url = str(source.get("source_url") or "")
        final_url = str(source.get("final_url") or "")
        if value and str(value) in {source_url, final_url}:
            verdict, confidence, reason = "review", 0.78, "pricing URL is the reviewed source URL"
        else:
            verdict, confidence, reason = "review", 0.60, "pricing URL needs manual review"
    elif field_path.startswith(("prices.", "treatments.", "medical_claims.", "outcomes.", "evidence.")):
        supported, reason = value_supported(value, haystack)
        verdict = "accepted" if supported else "review"
        confidence = 0.88 if supported else 0.58

    verified = dict(claim)
    verified["verifier_verdict"] = verdict
    verified["verifier_confidence"] = confidence
    verified["verifier_reason"] = reason
    return verified


def verify_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    claims = extraction.get("field_claims") or []
    if not isinstance(claims, list):
        claims = []
    verified_claims = [
        verify_claim(claim, extraction)
        for claim in claims
        if isinstance(claim, dict)
    ]
    decisions = decide_many(verified_claims)
    counts: dict[str, int] = {}
    for claim in verified_claims:
        verdict = str(claim.get("verifier_verdict") or "review")
        counts[verdict] = counts.get(verdict, 0) + 1
    return {
        "workflow": "VERIFY_CLINIC_PROFILE",
        "mode": "shadow",
        "source_url": (extraction.get("source") or {}).get("source_url"),
        "verified_claims": verified_claims,
        "rule_decisions": decisions,
        "quality_warnings": extraction.get("quality_warnings") or [],
        "summary": {
            "claims": len(verified_claims),
            "verdicts": counts,
            "actions": action_counts(decisions),
        },
    }


def action_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        action = str(decision.get("action") or "review")
        counts[action] = counts.get(action, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("extraction_json", type=Path, help="JSON output from extract_clinic_profile_shadow.py.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.extraction_json.open(encoding="utf-8") as handle:
        extraction = json.load(handle)
    if not isinstance(extraction, dict):
        raise SystemExit("extraction_json must contain an object")
    print(json.dumps(verify_extraction(extraction), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
