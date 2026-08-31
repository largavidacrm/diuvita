#!/usr/bin/env python3
"""Checks for exporting specialist claim proposals safely."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from export_specialist_claim_proposals import (
    ROOT,
    assert_safe_output_path,
    build_export,
    clean_sources,
    format_export,
    proposal_from_row,
    today_batch_name,
    write_export,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sample_report() -> dict:
    return {
        "clinics": [
            {
                "slug": "clinic-ready",
                "clinic_name": "Clinic Ready",
                "pending_professionals": ["Dra. Ana López", "Dr. Luis Pérez"],
                "pending_professional_count": 2,
                "review_card_count": 0,
                "claim_source_urls_clean": [
                    "https://clinic-ready.example/equipo/",
                    "https://clinic-ready.example/equipo/",
                    "",
                ],
            },
            {
                "slug": "clinic-with-card",
                "clinic_name": "Clinic With Card",
                "pending_professionals": ["Dra. Carla Ruiz"],
                "pending_professional_count": 1,
                "review_card_count": 1,
                "claim_source_urls_clean": ["https://clinic-with-card.example/team/"],
            },
            {
                "slug": "clinic-empty",
                "clinic_name": "Clinic Empty",
                "pending_professionals": [],
                "pending_professional_count": 0,
                "review_card_count": 0,
                "claim_source_urls_clean": [],
            },
        ]
    }


def exits(func, *args, **kwargs) -> bool:
    try:
        func(*args, **kwargs)
    except SystemExit:
        return True
    return False


def main() -> None:
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    report = sample_report()
    proposal = proposal_from_row(report["clinics"][0])
    export = build_export(report, batch="specialist-test")
    output = format_export(export)

    check(today_batch_name(now) == "specialist-claim-proposals-2026-08-31", "batch date missing")
    check(
        clean_sources(["https://clinic.example", "https://clinic.example", "not-url"])
        == ["https://clinic.example"],
        "sources should keep only unique URLs",
    )
    check(proposal is not None, "ready clinic should produce a proposal")
    check(proposal["slug"] == "clinic-ready", "proposal slug missing")
    check(proposal["source_url"] == "https://clinic-ready.example/equipo/", "first source missing")
    check(proposal["proposed_fields"]["profesionales"] == ["Dra. Ana López", "Dr. Luis Pérez"], "people missing")
    check(export["writes_data"] is False, "export must stay read-only")
    check(export["summary"]["proposal_count"] == 1, "proposal count missing")
    check(export["summary"]["skipped_with_open_cards"] == 1, "existing-card skip missing")
    check(export["summary"]["skipped_without_pending_names"] == 1, "empty-clinic skip missing")
    check(len(export["proposals"]) == 1, "only ready clinic should be exported")
    check("clinic-ready: 2 especialistas, 1 fuente, P55" in output, "formatted proposal summary missing")
    check("Dra. Ana López" not in output, "plain output should not print proposed names")
    check("Crear tarjetas de revisión requiere un paso aparte" in output, "safety note missing")

    include_existing = build_export(report, batch="specialist-test", include_existing_cards=True)
    check(include_existing["summary"]["proposal_count"] == 2, "include-existing mode should export both pending clinics")

    repo_target = ROOT / "data" / "private-specialist-proposals.json"
    check(exits(assert_safe_output_path, repo_target), "repo output should be blocked by default")
    allowed = assert_safe_output_path(repo_target, allow_repo_output=True)
    check(allowed.name == "private-specialist-proposals.json", "explicit repo output override missing")

    with TemporaryDirectory() as tmp:
        target = write_export(export, Path(tmp) / "specialists.json")
        check(target.is_file(), "export file should be written outside repo")
        check("Dra. Ana López" in target.read_text(encoding="utf-8"), "JSON output should keep proposed names")

    print("OK specialist claim proposal export: read-only batch is safe")


if __name__ == "__main__":
    main()
