#!/usr/bin/env python3
"""Checks for the official website source seeder."""

from seed_visible_clinic_sources import (
    format_report,
    insert_sources_sql,
    json_report,
    safe_limit,
    seed_candidates_sql,
    source_metadata,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    candidates = [
        {
            "slug": "clinic-a",
            "clinic_name": "Clinic A",
            "city": "Madrid",
            "country": "España",
            "status": "published",
            "website": "https://clinic-a.example/",
        },
        {
            "slug": "clinic-b",
            "clinic_name": "Clinic B",
            "city": "Barcelona",
            "country": "España",
            "status": "preliminary",
            "website": "https://clinic-b.example/",
        },
    ]
    result = {
        "generated_at": "2026-08-30T18:00:00+00:00",
        "inserted": [
            {
                "source_title": "Clinic A · web oficial",
                "source_url": "https://clinic-a.example/",
                "source_type": "official_website",
            },
            {
                "source_title": "Clinic B · web oficial",
                "source_url": "https://clinic-b.example/",
                "source_type": "official_website",
            },
        ],
    }
    dry_report = format_report(candidates=candidates, apply=False)
    apply_report = format_report(candidates=candidates, apply=True, result=result)
    dry_json = json_report(candidates=candidates, apply=False)
    apply_json = json_report(candidates=candidates, apply=True, result=result)
    candidate_sql = seed_candidates_sql(200)
    insert_sql = insert_sources_sql(20)
    metadata = source_metadata()

    check(safe_limit(0) == 1, "limit should have a lower bound")
    check(safe_limit(200) == 100, "limit should have an upper bound")
    check("limit 100" in candidate_sql, "candidate SQL should cap limits")
    check("public.normalized_url_host" in candidate_sql, "candidate SQL should dedupe by normalized host")
    check("public.normalized_url_host" in insert_sql, "insert SQL should dedupe by normalized host")
    check("official_website" in insert_sql, "insert SQL should store official source type")
    check("profile_fields_changed" in insert_sql, "insert SQL should preserve no-profile-edit metadata")
    check(metadata["profile_fields_changed"] is False, "metadata should mark no profile edits")
    check(metadata["requires_human_review"] is False, "metadata should not create review pressure")
    check("# Diuvita: siembra de fuentes oficiales" in dry_report, "title missing")
    check("Writes data: no" in dry_report, "dry run signal missing")
    check("Fuentes candidatas: 2" in dry_report, "candidate count missing")
    check("Clinic A · Madrid · published · https://clinic-a.example/" in dry_report, "candidate row missing")
    check("Writes data: yes" in apply_report, "apply signal missing")
    check("Fuentes guardadas: 2" in apply_report, "insert count missing")
    check("Clinic B · web oficial" in apply_report, "inserted source title missing")
    check("no edita fichas" in apply_report, "safety note missing")
    check(dry_json["mode"] == "dry_run", "dry JSON mode missing")
    check(dry_json["writes_data"] is False, "dry JSON should be read-only")
    check(dry_json["candidates_seen"] == 2, "dry JSON candidate count missing")
    check(dry_json["items"][0]["clinic_name"] == "Clinic A", "dry JSON items missing")
    check(apply_json["mode"] == "apply", "apply JSON mode missing")
    check(apply_json["writes_data"] is True, "apply JSON should show writes")
    check(apply_json["inserted_count"] == 2, "apply JSON insert count missing")
    check("publish" in apply_json["safety"], "JSON safety note missing")
    print("OK official source seeder: visible clinic websites can be stored as provenance")


if __name__ == "__main__":
    main()
