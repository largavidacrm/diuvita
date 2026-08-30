#!/usr/bin/env python3
"""Checks for the CTO shadow cycle orchestrator."""
from argparse import Namespace

from run_cto_shadow_cycle import build_steps, compact_summary, try_parse_json


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    check(try_parse_json('{"ok": true}')["ok"] is True, "JSON output should parse")
    check(try_parse_json("plain text") is None, "plain text should not parse")
    check(try_parse_json("") is None, "empty output should be None")
    compact = compact_summary("evaluate_claim_rules", {
        "summary": {"actions": {"review": 2}},
        "evaluations": [{"id": "a"}, {"id": "b"}],
    })
    check(compact["evaluations_count"] == 2, "evaluation count should be kept")
    check("evaluations" not in compact, "full evaluations should be removed")
    compact_items = compact_summary("monitor_source_changes", {
        "changed": 0,
        "items": [
            {
                "source_url": "https://a.test",
                "clinic_name": "A",
                "status": "unchanged",
                "snapshot": {"large": True},
            },
            {
                "source_url": "https://b.test",
                "clinic_name": "B",
                "status": "changed",
                "snapshot": {"large": True},
            },
        ],
    })
    check(compact_items["items_count"] == 2, "items count should be kept")
    check("items" not in compact_items, "full item list should be removed")
    check("snapshot" not in compact_items["sample_items"][0], "large nested snapshot should be omitted")
    compact_top_sources = compact_summary("measure_source_snapshot_retention", {
        "summary": {"total_snapshots": 2},
        "top_sources": [
            {"clinic_name": "A", "source_url": "https://a.test", "snapshots": 3, "prunable": 0, "source_record_id": "large"},
            {"clinic_name": "B", "source_url": "https://b.test", "snapshots": 1, "prunable": 0, "source_record_id": "large"},
        ],
    })
    check(compact_top_sources["top_sources_count"] == 2, "top source count should be kept")
    check("top_sources" not in compact_top_sources, "full top source list should be removed")
    check("source_url" in compact_top_sources["sample_top_sources"][0], "source url should distinguish compact top sources")
    check("source_record_id" not in compact_top_sources["sample_top_sources"][0], "large source ids should be omitted")
    compact_profiles = compact_summary("measure_profile_completeness", {
        "summary": {"visible_clinics": 2},
        "pending_profiles": [
            {
                "clinic_name": "A",
                "slug": "a",
                "status": "published",
                "pending_count": 3,
                "pending_fields": ["Email o teléfono"],
                "raw": {"large": True},
            }
        ],
    })
    check(compact_profiles["pending_profiles_count"] == 1, "pending profile count should be kept")
    check("pending_profiles" not in compact_profiles, "full pending profile list should be removed")
    check("pending_fields" in compact_profiles["sample_pending_profiles"][0], "pending fields should be kept")
    check("raw" not in compact_profiles["sample_pending_profiles"][0], "large profile details should be omitted")
    compact_digest = compact_summary("admin_digest", {
        "admin_email": "admin@example.test",
        "summary": {"reviews": {"open": 2}},
        "open_reviews": [
            {"title": "A", "review_type": "candidate_clinic", "priority": 90, "payload": {"large": True}},
            {"title": "B", "review_type": "clinic_quality_audit", "priority": 80, "payload": {"large": True}},
        ],
        "review_examples_by_type": [
            {"title": "A", "review_type": "candidate_clinic", "priority": 90, "payload": {"large": True}},
            {"title": "B", "review_type": "blocking_claim_review", "priority": 85, "payload": {"large": True}},
        ],
        "review_backlog_quality": {
            "duplicate_enrichment_clinics": 1,
            "duplicate_enrichment_reviews": 2,
            "raw": {"large": True},
        },
    })
    check("admin_email" not in compact_digest, "admin email should be removed from cycle output")
    check(compact_digest["open_reviews_count"] == 2, "open review count should be kept")
    check("payload" not in compact_digest["sample_open_reviews"][0], "review payload should be omitted")
    check(compact_digest["review_backlog_quality"]["duplicate_enrichment_clinics"] == 1, "review backlog quality should be kept")
    check("raw" not in compact_digest["review_backlog_quality"], "large review backlog payloads should be omitted")
    check(compact_digest["review_examples_by_type_count"] == 2, "review example count should be kept")
    check("payload" not in compact_digest["sample_review_examples_by_type"][0], "review example payload should be omitted")
    compact_health = compact_summary("check_production_health", {
        "base_url": "https://www.diuvita.com",
        "ok": True,
        "checks": [
            {
                "name": "home",
                "url": "https://www.diuvita.com/",
                "status": 200,
                "ok": True,
                "missing_markers": [],
                "body": "large",
            }
        ],
    })
    check(compact_health["checks_count"] == 1, "production health check count should be kept")
    check("checks" not in compact_health, "full production health checks should be removed")
    check("body" not in compact_health["sample_checks"][0], "production response bodies should be omitted")
    compact_source_shadow = compact_summary("submit_source_shadow_reviews", {
        "items": [
            {
                "clinic_slug": "example",
                "clinic_name": "Example",
                "source_url": "https://example.test",
                "status": "ready",
                "proposed_fields": ["email"],
                "verification_summary": {"large": True},
            }
        ],
    })
    check(compact_source_shadow["items_count"] == 1, "source shadow count should be kept")
    check("verification_summary" not in compact_source_shadow["sample_items"][0], "large source shadow details should be omitted")
    steps = build_steps(Namespace(
        apply_safe=False,
        review_limit=2,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=0,
        source_shadow_clinic_slug=None,
        source_shadow_replace_existing=False,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        profile_completeness_limit=11,
        fetch_timeout=7,
        strict_editorial=False,
        production_health=False,
        production_base_url="https://www.diuvita.com",
        production_timeout=7,
    ))
    names = [step[0] for step in steps]
    check("process_source_change_reviews" in names, "source-change processing step missing")
    check("submit_source_shadow_reviews" not in names, "source shadow batch should be off by default")
    check("check_operational_limits_strict" not in names, "strict editorial scan should be off by default")
    check("check_production_health" not in names, "production health should be off by default")
    check("submit_blocking_claim_reviews" in names, "blocking-claim review step missing")
    check("measure_source_snapshot_retention" in names, "source snapshot retention step missing")
    check("evaluate_claim_rules" in names, "claim rule evaluation step missing")
    source_change_step = [step for step in steps if step[0] == "process_source_change_reviews"][0]
    check("8" in source_change_step[1], "source-change limit should be passed through")
    blocking_step = [step for step in steps if step[0] == "submit_blocking_claim_reviews"][0]
    check("9" in blocking_step[1], "blocking-claim limit should be passed through")
    retention_step = [step for step in steps if step[0] == "measure_source_snapshot_retention"][0]
    check("--json" in retention_step[1], "retention report should be machine readable")
    check("180" in retention_step[1] and "3" in retention_step[1] and "7" in retention_step[1], "retention settings should pass through")
    profile_step = [step for step in steps if step[0] == "measure_profile_completeness"][0]
    check("--json" in profile_step[1], "profile completeness should be machine readable")
    check("11" in profile_step[1], "profile completeness limit should pass through")
    digest_step = [step for step in steps if step[0] == "admin_digest"][0]
    check("--json" in digest_step[1], "admin digest should be machine readable")
    claim_step = [step for step in steps if step[0] == "evaluate_claim_rules"][0]
    check("--json" in claim_step[1], "claim rule evaluation should be machine readable")
    check("6" in claim_step[1], "claim limit should be passed through")
    optional_steps = build_steps(Namespace(
        apply_safe=True,
        review_limit=2,
        source_limit=3,
        monitor_limit=4,
        source_change_limit=8,
        source_shadow_limit=2,
        source_shadow_clinic_slug="sensabell",
        source_shadow_replace_existing=True,
        digest_limit=5,
        claim_limit=6,
        blocking_claim_limit=9,
        snapshot_retention_days=180,
        snapshot_keep_latest=3,
        snapshot_retention_limit=7,
        profile_completeness_limit=11,
        fetch_timeout=7,
        strict_editorial=True,
        production_health=True,
        production_base_url="https://www.diuvita.com",
        production_timeout=7,
    ))
    source_shadow_step = [step for step in optional_steps if step[0] == "submit_source_shadow_reviews"][0]
    check("--apply" in source_shadow_step[1], "source shadow batch should follow safe apply mode")
    check("--clinic-slug" in source_shadow_step[1] and "sensabell" in source_shadow_step[1], "source shadow clinic slug should pass through")
    check("--replace-existing" in source_shadow_step[1], "source shadow replace flag should pass through")
    strict_step = [step for step in optional_steps if step[0] == "check_operational_limits_strict"][0]
    check("--strict-editorial" in strict_step[1], "strict editorial flag should pass through")
    health_step = [step for step in optional_steps if step[0] == "check_production_health"][0]
    check(optional_steps.index(strict_step) < optional_steps.index(health_step), "strict editorial should run before production health")
    check("--json" in health_step[1], "production health should be machine readable")
    check("https://www.diuvita.com" in health_step[1], "production health base URL should pass through")
    check("7" in health_step[1], "production health timeout should pass through")
    print("OK cycle: CTO shadow orchestration")


if __name__ == "__main__":
    main()
