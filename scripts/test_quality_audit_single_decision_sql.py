#!/usr/bin/env python3
"""Checks future quality audits create one review card per missing field."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "0024_single_issue_quality_audits.sql"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    for marker in [
        "create or replace function public.admin_complete_quality_audit_job",
        "for issue_item in select value from jsonb_array_elements(issues)",
        "'single_decision', true",
        "'quality_issue_code', issue_code",
        "'quality_issue_label', issue_label",
        "'issues', jsonb_build_array(issue_item)",
        "field_path",
        "issue_field_path := case issue_code",
        "'one_decision_reviews', true",
        "rq.payload ->> 'quality_issue_code' = issue_code",
        "rq.payload -> 'issues' @> jsonb_build_array(jsonb_build_object('code', issue_code))",
        "coalesce(rq.payload ->> 'quality_context', '') <> 'blocking_claims'",
        "review_count := review_count + 1",
        "grant execute on function public.admin_complete_quality_audit_job(uuid, integer) to authenticated",
    ]:
        check(marker in sql, f"missing single-decision quality audit SQL marker: {marker}")

    for field_path in [
        "profile.website",
        "profile.summary",
        "services.list",
        "specialties.list",
        "units.list",
        "team.professionals",
        "technology.highlighted",
        "location.locations",
        "contact.public",
    ]:
        check(field_path in sql, f"missing field_path mapping: {field_path}")

    clinic_loop = sql[sql.index("for clinic_row in"):sql.index("scanned_count := scanned_count + 1;")]
    check("review_queue" not in clinic_loop, "clinic scan should not skip a clinic just because another quality card is open")
    insert_payload = sql[sql.index("jsonb_build_object("):sql.rindex("grant execute")]
    check("'issues', issues" not in insert_payload, "review payload should not store the full multi-issue array")
    check("Completar ficha:" not in sql, "new quality audit cards should use manual-review wording")

    print("OK quality audit SQL: future reviews stay one field per card")


if __name__ == "__main__":
    main()
