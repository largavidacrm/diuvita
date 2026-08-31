#!/usr/bin/env python3
"""Checks that blocking-claim review cards have clear admin labels."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")

    for marker in [
        "function isBlockingClaimReview",
        "function reviewVisibleLabel",
        "function reviewMatchesType",
        "function blockingClaimStatuses",
        "function reviewRecommendedStep",
        "function renderReviewGuidance",
        "function reviewWarningItems",
        'id="reviewWarningPanel"',
        'id="reviewWarningList"',
        "Advertencias imprescindibles",
        "Mantén ese dato fuera de publicación",
        "Claim bloqueante",
        "Claims bloqueantes",
        'payload.quality_context === "blocking_claims"',
        'value === "blocking_claim_review"',
        "reviewVisibleLabel(row)",
        "reviewVisibleLabel(activeReview)",
    ]:
        check(marker in index, f"missing blocking-claim label marker: {marker}")

    check(
        'row.review_type === "clinic_quality_audit" && !isBlockingClaimReview(row)' in index,
        "quality-audit summary should separate blocking-claim cards",
    )
    print("OK admin labels: blocking claims are distinct")


if __name__ == "__main__":
    main()
