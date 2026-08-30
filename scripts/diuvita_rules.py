#!/usr/bin/env python3
"""Deterministic publication rules for Diuvita field claims.

The AI creates claims. This module decides whether a claim is eligible for
publication, human review, or rejection. Defaults are deliberately conservative.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any


LOW_RISK_PREFIXES = (
    "identity.",
    "location.",
    "contact.website",
    "contact.email",
    "contact.phone",
    "contact.instagram",
)

MEDIUM_RISK_PREFIXES = (
    "services.",
    "specialties.",
    "units.",
    "diagnostics.",
    "programs.",
    "technologies.",
    "professionals.published",
    "team.public_professionals",
    "transparency.years_in_practice",
    "transparency.specialists_count",
)

HIGH_RISK_PREFIXES = (
    "team.credentialing_visible",
    "team.credentials",
    "prices.",
    "treatments.",
    "medical_claims.",
    "outcomes.",
    "evidence.",
)

SUPPORTED_VERDICTS = {
    "accepted",
    "rejected",
    "stale",
    "conflict",
    "review",
    "unknown",
}


@dataclass(frozen=True)
class RiskPolicy:
    auto_publish_enabled: bool = False
    low_auto_publish_enabled: bool = True
    medium_auto_publish_enabled: bool = False
    high_auto_publish_enabled: bool = False
    reject_below_confidence: float = 0.60
    low_confidence_threshold: float = 0.90
    medium_confidence_threshold: float = 0.93
    high_confidence_threshold: float = 0.98
    high_min_sources: int = 2


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "si", "sí"}
    return bool(value)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def field_risk(field_path: str) -> str:
    clean = (field_path or "").strip().lower()
    if any(clean.startswith(prefix) for prefix in HIGH_RISK_PREFIXES):
        return "high"
    if any(clean.startswith(prefix) for prefix in MEDIUM_RISK_PREFIXES):
        return "medium"
    if any(clean.startswith(prefix) for prefix in LOW_RISK_PREFIXES):
        return "low"
    return "high"


def risk_threshold(risk: str, policy: RiskPolicy = RiskPolicy()) -> float:
    if risk == "low":
        return policy.low_confidence_threshold
    if risk == "medium":
        return policy.medium_confidence_threshold
    return policy.high_confidence_threshold


def combined_confidence(claim: dict[str, Any]) -> float:
    extractor = _as_float(
        claim.get("extractor_confidence", claim.get("confidence")),
        default=0.0,
    )
    verifier = _as_float(
        claim.get("verifier_confidence", claim.get("verification_confidence")),
        default=extractor,
    )
    if extractor and verifier:
        return min(extractor, verifier)
    return max(extractor, verifier)


def _decision(action: str, risk: str, confidence: float, reason: str) -> dict[str, Any]:
    return {
        "action": action,
        "risk": risk,
        "confidence": round(confidence, 4),
        "reason": reason,
    }


def decide_claim(claim: dict[str, Any], policy: RiskPolicy = RiskPolicy()) -> dict[str, Any]:
    field_path = str(claim.get("field_path") or claim.get("field") or "")
    risk = field_risk(field_path)
    confidence = combined_confidence(claim)
    verdict = str(claim.get("verifier_verdict") or claim.get("verification_status") or "unknown").lower()
    source_count = _as_int(claim.get("source_count", claim.get("sources_count", 0)))

    if verdict not in SUPPORTED_VERDICTS:
        verdict = "unknown"

    if _as_bool(claim.get("human_locked")):
        return _decision("review", risk, confidence, "human locked value cannot be overwritten")

    if _as_bool(claim.get("has_conflict")) or verdict == "conflict":
        return _decision("review", risk, confidence, "conflicting evidence")

    if verdict == "rejected":
        return _decision("reject", risk, confidence, "verifier rejected the claim")

    if confidence < policy.reject_below_confidence:
        return _decision("reject", risk, confidence, "confidence below rejection floor")

    if source_count <= 0:
        return _decision("review", risk, confidence, "missing source")

    if verdict in {"unknown", "review"}:
        return _decision("review", risk, confidence, "verifier did not accept the claim")

    if verdict == "stale" or _as_bool(claim.get("source_stale")):
        return _decision("review", risk, confidence, "source may be stale")

    required = risk_threshold(risk, policy)
    if confidence < required:
        return _decision("review", risk, confidence, f"confidence below {required:.2f} threshold")

    if risk == "high" and source_count < policy.high_min_sources:
        return _decision("review", risk, confidence, "high-risk claim needs multiple sources")

    if not policy.auto_publish_enabled:
        return _decision("review", risk, confidence, "auto-publish is off")

    if risk == "low" and policy.low_auto_publish_enabled:
        return _decision("auto_accept", risk, confidence, "low-risk claim passed rules")

    if risk == "medium" and policy.medium_auto_publish_enabled:
        return _decision("auto_accept", risk, confidence, "medium-risk claim passed rules")

    if risk == "high" and policy.high_auto_publish_enabled:
        return _decision("auto_accept", risk, confidence, "high-risk claim passed strict rules")

    return _decision("review", risk, confidence, f"{risk}-risk auto-publish is disabled")


def decide_many(claims: list[dict[str, Any]], policy: RiskPolicy = RiskPolicy()) -> list[dict[str, Any]]:
    return [
        {
            "field_path": claim.get("field_path") or claim.get("field"),
            **decide_claim(claim, policy),
        }
        for claim in claims
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("claims_json", help="JSON file with a claim object or a list of claims.")
    parser.add_argument("--auto-publish", action="store_true")
    parser.add_argument("--allow-medium", action="store_true")
    parser.add_argument("--allow-high", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with open(args.claims_json, encoding="utf-8") as handle:
        data = json.load(handle)
    claims = data if isinstance(data, list) else [data]
    if not all(isinstance(claim, dict) for claim in claims):
        raise SystemExit("claims_json must contain an object or a list of objects")
    policy = RiskPolicy(
        auto_publish_enabled=args.auto_publish,
        medium_auto_publish_enabled=args.allow_medium,
        high_auto_publish_enabled=args.allow_high,
    )
    print(json.dumps(decide_many(claims, policy), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
