#!/usr/bin/env python3
"""Checks for safe manual profile-enrichment review submission."""
import inspect

from submit_profile_enrichment_reviews import create_review


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    proposal = {
        "slug": "clinic-a",
        "title": "Ampliar ficha: Clinic A",
        "priority": 45,
        "proposed_fields": {
            "profesionales": ["Dra. Laura García Pérez"],
        },
    }
    signature = inspect.signature(create_review)
    check(
        signature.parameters["allow_multiple_open_clinic_reviews"].default is False,
        "manual enrichment should allow only one open clinic card by default",
    )

    captured = {}

    def fake_run_psql(sql, local_env):
        captured["sql"] = sql
        return '[{"status": "existing_clinic", "id": "review-1", "title": "Open review"}]'

    original_run_psql = create_review.__globals__["run_psql"]
    try:
        create_review.__globals__["run_psql"] = fake_run_psql
        result = create_review("manual-batch", proposal, "admin@example.test", {})
    finally:
        create_review.__globals__["run_psql"] = original_run_psql

    check(result["status"] == "existing_clinic", "same-clinic open review should be reported")
    sql = captured.get("sql", "")
    check("open_clinic_reviews as" in sql, "same-clinic duplicate guard missing")
    check("existing_clinic as" in sql, "same-clinic existing review CTE missing")
    check(
        "and (false or not exists (select 1 from existing_clinic))" in sql,
        "manual review insert should be blocked when another clinic review is open",
    )
    check(
        "rq.payload ->> 'proposal_batch' = 'manual-batch'" in sql,
        "same-batch review should still be detected first",
    )
    print("OK profile enrichment reviews: same-clinic duplicates guarded")


if __name__ == "__main__":
    main()
