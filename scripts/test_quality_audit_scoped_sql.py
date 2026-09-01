#!/usr/bin/env python3
"""Checks quality audits can be scoped to one clinic and one requested field."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "0027_scoped_quality_audit_jobs.sql"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")

    for marker in [
        "create or replace function public.admin_complete_quality_audit_job",
        "target_clinic_id := nullif(btrim(coalesce(job_row.input ->> 'clinic_id', '')), '')",
        "or c.id::text = target_clinic_id",
        "jsonb_array_elements_text(",
        "requested_field_keys",
        "requested_issue_codes",
        "when 'profesionales' then 'missing_professionals'",
        "when 'summary' then 'weak_summary'",
        "when 'services' then 'missing_services'",
        "when 'locations' then 'missing_address'",
        "when 'maps_url' then 'missing_maps_url'",
        "where coalesce(filtered.value ->> 'code', '') = any(requested_issue_codes)",
        "'target_scope'",
        "'field_scope'",
        "'requested_fields'",
        "'clinic_id', target_clinic_id",
        "grant execute on function public.admin_complete_quality_audit_job(uuid, integer) to authenticated",
    ]:
        check(marker in sql, f"missing scoped quality-audit SQL marker: {marker}")

    check("missing_maps_url" in sql and "location.maps_url" in sql, "Google Maps missing-field audit should be addressable")
    check("'all_visible_clinics'" in sql and "'selected_clinic'" in sql, "clinic scope labels should be persisted")
    check("'all_quality_fields'" in sql and "'operator_selected_fields'" in sql, "field scope labels should be persisted")

    print("OK quality audit SQL: scoped clinic and field audits are supported")


if __name__ == "__main__":
    main()
